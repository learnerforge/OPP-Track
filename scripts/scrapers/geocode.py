"""
Address geocoding via OpenStreetMap Nominatim.

Turns the free-text ``location`` string a scraper captured (a city, a venue
name, or a full street address) into real coordinates, so the frontend can sort
opportunities by true distance from the viewer instead of guessing from a
hand-written gazetteer.

Why Nominatim: it needs no API key, its data is open, and it resolves Indian
venue names that a static table never could ("Myladi" -> an actual hamlet in
Kerala). The trade-offs are handled explicitly here:

* **One request per second.** Nominatim's usage policy requires it. ``geocode()``
  sleeps to enforce the interval across the whole process.
* **A real User-Agent, always.** Requests without one are blocked outright.
* **Permanent cache.** ``data/location_cache.json`` keys the address -> result,
  so an address is geocoded exactly once ever. A full pass over the catalogue is
  therefore a few hundred requests the first time and *zero* on every later run.
* **Never fatal.** A timeout, a 4xx, a bad response — all degrade to "no
  coordinates", which the callers treat as "sorts last". Geocoding can never
  break a scrape.

The output is a side file, ``public/data/locations.json`` — see
``write_locations_file`` — so the frozen ``src/`` tree and the record schema are
both untouched.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

# Nominatim requires a descriptive UA identifying the application.
USER_AGENT = "OPP-Track/1.0 (opportunity tracker; https://github.com/learnerforge/OPP-Track)"

ENDPOINT = "https://nominatim.openstreetmap.org/search"

# Minimum seconds between requests, per the Nominatim usage policy.
MIN_INTERVAL_S = 1.0

# Coordinates are emitted to this many decimals (~11 m at the equator), which
# is far more than a "nearest event" sort needs and keeps the file small.
PRECISION = 5

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_FILE = REPO_ROOT / "data" / "location_cache.json"
LOCATIONS_FILE = REPO_ROOT / "public" / "data" / "locations.json"

_last_request_at = 0.0


def _throttle() -> None:
    """Sleep so consecutive calls are at least MIN_INTERVAL_S apart."""
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_INTERVAL_S:
        time.sleep(MIN_INTERVAL_S - elapsed)
    _last_request_at = time.monotonic()


def load_cache() -> dict[str, dict | None]:
    """Read the permanent address -> coordinates cache (empty if missing)."""
    try:
        raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def save_cache(cache: dict[str, dict | None]) -> None:
    """Write the cache back, sorted for a stable diff across runs."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ordered = {k: cache[k] for k in sorted(cache)}
    CACHE_FILE.write_text(
        json.dumps(ordered, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _query(address: str) -> dict | None:
    """One Nominatim lookup. Returns {'lat','lon','display'} or None."""
    params = urllib.parse.urlencode(
        {"q": address, "format": "jsonv2", "limit": 1, "addressdetails": 0}
    )
    req = urllib.request.Request(
        f"{ENDPOINT}?{params}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    _throttle()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("  geocode failed for %r: %s", address, exc)
        return None

    if not isinstance(payload, list) or not payload:
        return None
    top = payload[0]
    try:
        return {
            "lat": round(float(top["lat"]), PRECISION),
            "lon": round(float(top["lon"]), PRECISION),
            "display": str(top.get("display_name", ""))[:160],
        }
    except (KeyError, TypeError, ValueError):
        return None


def geocode(address: str, cache: dict[str, dict | None] | None = None) -> dict | None:
    """
    Resolve one address to coordinates, consulting and filling ``cache``.

    ``cache`` is mutated in place (and should be persisted by the caller with
    ``save_cache`` after a batch), so a long run does not lose its work. A
    ``None`` result is cached too: a genuinely un-geocodable string must not be
    retried on every single run.
    """
    key = " ".join(address.split()).strip()
    if not key:
        return None
    if cache is not None and key in cache:
        return cache[key]

    result = _query(key)

    # Fallback: a long venue address often misses, but its trailing
    # "City, State, Country" usually resolves. Retry with the tail only.
    if result is None and "," in key:
        parts = [p.strip() for p in key.split(",") if p.strip()]
        for take in (2, 1):
            if len(parts) > take:
                tail = ", ".join(parts[-take:])
                result = _query(tail)
                if result:
                    break

    if cache is not None:
        cache[key] = result
    return result


# Strings that name no place at all. Deliberately NOT `classify_location`:
# that function returns "Online" as its *default* for any unrecognised text
# (see base.py — "Mumbai, Maharashtra, India" classifies as "Online" because
# "Mumbai" is not an offline keyword), so it cannot tell a city from a webinar.
# This check asks the narrower question the geocoder actually cares about:
# "could this string possibly denote a physical place?"
_NON_PLACE_RE = re.compile(
    r"^\s*$"
    r"|^\s*(online|remote|virtual|anywhere|worldwide|global|hybrid|wfh|"
    r"work\s+from\s+home|various(\s*\(.*\))?|offline|in[- ]person|prize|"
    r"registering|upcoming|tba|tbd|n/?a|none|null|-+)\s*$",
    re.I,
)


def is_geocodable(location: str) -> bool:
    """
    True when a location string names a physical place worth geocoding.

    Rejects blanks, online/remote indicators, and scraper artefacts
    ("Various", "Prize", "UPCOMING", "TBA"). Accepts anything else — including
    a bare city name, a venue, or a full street address.
    """
    if not location:
        return False
    return _NON_PLACE_RE.search(location) is None


def geocode_dataset(
    items: list[dict],
    cache: dict[str, dict | None] | None = None,
    verbose: bool = True,
) -> dict[str, dict]:
    """
    Geocode every distinct physical location in a dataset.

    Returns a mapping of ``location string -> {lat, lon, display}``. Distinct
    locations only: the catalogue has 2,588 records but far fewer unique
    location strings, and the cache makes repeat runs free.
    """
    if cache is None:
        cache = load_cache()

    wanted = sorted(
        {it.get("location", "").strip() for it in items if is_geocodable(it.get("location", ""))}
    )
    logger.info("Geocoding %d distinct physical location(s)", len(wanted))

    resolved: dict[str, dict] = {}
    misses = 0
    for i, address in enumerate(wanted, 1):
        hit = geocode(address, cache)
        if hit:
            resolved[address] = hit
        else:
            misses += 1
        if verbose and (i % 25 == 0 or i == len(wanted)):
            logger.info("  %d/%d addressed, %d unresolved", i, len(wanted), misses)

    logger.info(
        "Geocoded %d/%d location(s); %d unresolved",
        len(resolved), len(wanted), misses,
    )
    return resolved


def write_locations_file(resolved: dict[str, dict]) -> Path:
    """
    Write the coordinates side file the frontend reads.

    Lives at ``public/data/locations.json`` so it ships as a static asset
    alongside the dataset — no schema change, and nothing under the frozen
    ``src/`` tree is touched.
    """
    LOCATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "count": len(resolved),
        "source": "OpenStreetMap Nominatim",
        "locations": {k: resolved[k] for k in sorted(resolved)},
    }
    LOCATIONS_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return LOCATIONS_FILE
