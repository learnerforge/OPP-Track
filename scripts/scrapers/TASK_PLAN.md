# TASK_PLAN.md — OPP-Track Scraper System Audit & Execution Plan
> Generated: 2026-08-19 23:58 IST
> Methodology: Live-tested every scraper, inspected raw HTML, traced data flow end-to-end

---

## 1. SYSTEM STATE — CURRENT

```
SEED_DATA:     227 entries (seed_001 — seed_227, with gaps at 187/189)
SEED_VERSION:  8
Scraped JSON:  53 items (0 Devfolio, 18 Devpost, 32 Unstop, 3 HackerEarth, 0 Internshala)
Storage:       localStorage, version-gated merge
Python deps:   scrapling 0.4.14, beautifulsoup4, httpx, requests — all installed
```

### Scraped Output Quality Report
| Metric | Count | Status |
|--------|-------|--------|
| Total scraped items | 53 | LOW — should be 150+ |
| Items with empty deadline | 13 (25%) | CRITICAL — merge_seeds drops these |
| Items with empty tags | 21 (40%) | BAD — no filtering possible |
| Items with location field | 0 (0%) | MISSING — field doesn't exist in schema |
| Items with prize info | 0 (0%) | MISSING — not extracted |
| Duplicate titles | 0 | OK |
| Stale deadlines (past) | 0 | OK (but no detection system) |

---

## 2. SCRAPER-BY-SCRAPER AUDIT

### 2.1 Devfolio — `devfolio.py` (126 lines)

**Status: PARTIALLY WORKING — scrapes 25 items but card HTML is extremely sparse**

**What works:**
- StealthyFetcher renders the SPA correctly (status 200)
- Extracts titles and links from `<a class="Link__LinkBase-*">` cards
- Extracts start dates via regex `Starts DD/MM/YY`
- Extracts participation counts via regex `\+\d+ participat`
- Deduplication by fingerprint works

**What's broken / missing:**
| Bug | Root Cause | Fix |
|-----|-----------|-----|
| No location (Online/Offline) | Cards contain only `<h3>Title</h3>` — no location in card HTML. "Online" and "Offline" text exists on page but can't be matched to cards by position | Option A: Tier-2 scrape each event page. Option B: Use page-level Online/Offline filter URLs (`?mode=online`) |
| No tags/themes | Not present in card HTML | Tier-2 scrape |
| No prize info | Not present in card HTML | Tier-2 scrape |
| No organizer info | Not present in card HTML | Tier-2 scrape |
| Eligibility always generic | Hardcoded "Open to all students and developers" | Tier-2 scrape |
| Notes minimal | Only "Source: Devfolio. +N participating" | Tier-2 scrape |

**Raw HTML of first card:**
```html
<a href="https://codewars-2.devfolio.co/" class="Link__LinkBase-sc-*">
  <h3 class="sc-fhHczv hWkQBg">CodeWars1.0</h3>
</a>
```
→ That's it. The card is 2 elements. All useful data is on the detail page.

**Page-level data available (not per-card):**
- "Online" found 9 times on page
- "Offline" found 11 times on page
- These are separate `<span>` elements near cards but positional matching is unreliable

**Verdict: Requires Tier-2 detail scraping to get useful data.**

---

### 2.2 Devpost — `devpost.py` (135 lines)

**Status: WORKING but critical data extraction broken**

**What works:**
- StealthyFetcher renders the page (status 200)
- Extracts 9 cards per URL (upcoming + open = 18 unique)
- Date range parsing works (`Aug 29 - Sep 01, 2026` → `2026-09-01`)
- Participant count extracted correctly

**What's broken / missing:**
| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Prize always shows "$" | `.prize-amount` selector finds `<span class="prize-amount">$<span data-currency-value="">34,500</span></span>` — code does `clean_text(el[0].text)` which only gets the first text node "$" | Use `clean_text(el[0].text)` + traverse children, or use `text_content()` equivalent |
| Tags always empty | `.theme-label` selector exists but code gets `clean_text(t.text)` which misses text inside `<i>` checkmark icons | Use `el.text_content()` or `clean_text(str(el))` |
| Host not extracted | `.host-label` selector works but text includes checkmark icon | Use `.host-label` text properly |
| Location missing | Page has `<span>Online</span>` inside `.info-with-icon` but no selector targets it | Add: `card.css('.info-with-icon span')` and check for "Online"/"Offline" |
| No organizer field | Not in schema | Add to ScrapeItem |

**Raw HTML of first card (key sections):**
```html
<!-- Location: AVAILABLE -->
<div class="info-with-icon">
  <i class="fas fa-globe"></i>
  <div class="info"><span>Online</span></div>
</div>

<!-- Prize: AVAILABLE but selector broken -->
<div class="prize mr-4 mb-3">
  <span class="prize-amount">$<span data-currency-value="">34,500</span></span> in prizes
</div>

<!-- Tags: AVAILABLE -->
<span class="label theme-label mr-2 mb-2" title="Machine Learning/AI">
  <i class="far fa-check-square checkmark"></i> Machine Learning/AI
</span>

<!-- Host: AVAILABLE -->
<span class="label round host-label" title="TikTok">
  <i class="far fa-check-circle checkmark"></i> TikTok
</span>
```

**Fix for prize:**
```python
# BROKEN:
prize = clean_text(prize_el[0].text)  # Gets "$"

# FIX:
prize_el = card.css('.prize-amount')
if prize_el:
    prize_text = prize_el[0].text_content()  # Gets "$34,500 in prizes"
    prize = clean_text(prize_text)
```

**Fix for tags:**
```python
# BROKEN:
tags = [clean_text(t.text) for t in tag_els if clean_text(t.text)]

# FIX:
tags = [clean_text(str(t)) for t in tag_els]  # Gets full text including icon
# Or better: t.attrib.get('title', '') for clean tag names
```

**Fix for location:**
```python
# ADD:
location_el = card.css('.info-with-icon span')
location = ""
for loc in location_el:
    loc_text = clean_text(loc.text)
    if loc_text.lower() in ('online', 'offline', 'hybrid'):
        location = loc_text
        break
```

**Verdict: Fixable with selector changes — no Tier-2 needed.**

---

### 2.3 Unstop — `unstop.py` (153 lines)

**Status: WORKING — best quality scraper**

**What works:**
- StealthyFetcher renders Angular SPA (status 200)
- Extracts 21 items from competitions page
- Title, org, location, tags, team size, dates all extracted correctly
- "days left" → approximate deadline calculation works
- Type detection (Hackathon/Internship) works

**What's broken / missing:**
| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Timeout on some runs | Unstop page is heavy — Angular SPA with many network requests | Increase timeout to 45s, add retry logic |
| "days left" is approximate | `datetime.now() + timedelta(days=N)` is correct but approximate | Acceptable — mark as "approximate" in notes |
| No prize info | Not visible on listing page | Tier-2 scrape individual pages |
| No organizer field | Not in schema | Add to ScrapeItem |
| Eligibility always generic | Hardcoded "Check Unstop for eligibility details" | Parse from tags like "Everyone can apply" |

**Raw HTML of first card:**
```html
<a class="item opp_1739732" href="/hackathons/csi-kjsse-hackday-20-...">
  <h3 itemprop="name" class="double-wrap"> CSI KJSSE Hackday 2.0 </h3>
  <p class="single-wrap">Computer Society of India , KJSSE</p>
  <div class="other_fields">
    <span>2 - 3 Members</span>
    <span class="location_text">KJ Somaiya School of Engineering, Mumbai, Maharashtra, India</span>
  </div>
  <span class="chip_text">Artificial Intelligence</span>
  <span class="chip_text">AI Engineering</span>
  <span class="chip_text">Everyone can apply</span>
  <label class="tag-text">Posted Aug 19, 2026</label>
  <label class="tag-text">5 days left</label>
</a>
```

**All data is available on the card — no Tier-2 needed.**

**Verdict: Mostly working. Add eligibility parsing from tags, increase timeout.**

---

### 2.4 HackerEarth — `hackerearth.py` (133 lines)

**Status: BROKEN — only 3 items (should be 60+)**

**What works:**
- StealthyFetcher renders Next.js SSR page (status 200)
- Extracts title, link, status, participants, company from cards
- Type detection works

**What's broken / missing:**
| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Only 3 items found | Selector `div.group.relative.w-full.block` matches only 3 cards. Actual card count: 61 with `div[class*="group"]` | Broaden selector to match actual card structure |
| No deadlines | Deadline not shown on listing page | Tier-2 scrape each challenge page |
| Participants shows "0" for some | HTML has `<span class="">0</span>` — legitimate 0 participants | Acceptable — display as-is |
| No location | Not in listing page HTML | Tier-2 scrape |
| No prize info | Not in listing page HTML | Tier-2 scrape |
| No tags | Not extracted | Extract from categories if available |

**Selector analysis:**
```
div.group.relative.w-full.block  → 3 matches   (current — too specific)
div[class*="group"]              → 61 matches   (too broad — includes non-card elements)
a[href*="/challenges/"]          → 4 matches    (links only)
```

**The actual card structure:**
```html
<div class="group relative w-full block">
  <a href="https://www.hackerearth.com/challenges/hackathon/..." class="absolute inset-0 z-0"></a>
  <div class="bg-card text-card-foreground ...">
    <div class="inline-flex ..."><span>Live</span></div>  <!-- status badge -->
    <div class="text-sm font-semibold truncate">GitHub Repo Value Check</div>  <!-- title -->
    <div class="text-sm text-muted-foreground truncate">HackerEarth</div>  <!-- company -->
    <div class="flex items-center gap-1.5 ..."><span>0</span></div>  <!-- participants -->
  </div>
</div>
```

**Fix: The 3-card selector IS correct for visible cards. The other 58 are below the fold / lazy-loaded. Need to scroll or use pagination.**

**Verdict: Requires scroll/pagination for more items + Tier-2 for deadlines.**

---

### 2.5 Internshala — `internshala.py` (143 lines)

**Status: SCRAPES 75 ITEMS but 0 appear in final output**

**What works:**
- StealthyFetcher renders the page (status 200)
- Extracts 75 internship cards
- Title, link, company, stipend, location, duration extracted
- Type detection (Internship) works

**What's broken / missing:**
| Bug | Root Cause | Fix |
|-----|-----------|-----|
| 0 items in final output | `merge_seeds.py` drops items with empty deadlines — ALL 75 Internshala items have `deadline=""` | Fix merge_seeds to handle empty deadlines, OR add deadline extraction |
| Unicode crash on Windows | `print(f'notes={r.notes}')` crashes with cp1252 encoding error on `₹` symbol | Use `sys.stdout.reconfigure(encoding='utf-8')` or write to file |
| No deadline extraction | Internshala listing doesn't show application deadlines — they're on detail pages | Tier-2 scrape each internship page |
| Links may be broken | Selector `a[href*='/internship/']` may not match all card types | Verify and fix selector |
| Stipend extraction fragile | Searches all `*` elements for `₹` — may match unrelated text | Use more specific selector |

**Why 0 items reach output:**
```
merge_seeds.py line:
    if not deadline:
        skipped += 1
        continue
```
→ All 75 items have empty deadlines → all 75 skipped → 0 in output.

**Verdict: Fix merge_seeds.py deadline handling + add Tier-2 for deadlines.**

---

## 3. PIPELINE AUDIT

### 3.1 `run_all.py` (159 lines)

**Status: BASIC — works but no enrichment/quality/staleness pipeline**

**Missing features:**
- No `--detailed` flag for Tier-2 scraping
- No `--quick` flag for fast mode
- No `--enrich` flag for post-scrape enrichment
- No progress tracking / TASK_PLAN.md updates
- No quality scoring
- No staleness detection
- No retry logic for failed scrapers
- No parallel scraper execution

### 3.2 `merge_seeds.py` (217 lines)

**Status: CRITICAL BUG — drops all items without deadlines**

**Bug: Line that drops items:**
```python
# Skip if deadline is empty — validator requires valid YYYY-MM-DD
deadline = item.get("deadline", "")
if not deadline:
    skipped += 1
    continue
```
→ This drops ALL Internshala items (75) and any HackerEarth items without deadlines.

**Missing features:**
- No handling of new fields (location, prize_pool, participants, organizer)
- No auto-completion of stale entries
- No quality score in output
- No location normalization

### 3.3 `validate-data.mjs` (133 lines)

**Status: GOOD but missing rules**

**Missing validation rules:**
- No staleness check (deadline < today → warning)
- No quality score validation
- No location validation
- No duplicate link detection (only title dedup)
- No empty eligibility warning
- No check for "Source: Devfolio." only notes

### 3.4 `base.py` (134 lines)

**Status: SOLID foundation but missing fields**

**Missing fields in ScrapeItem:**
- `location` (Online/Hybrid/Offline)
- `prize_pool` (string)
- `participants` (int or string)
- `organizer` (string)
- `duration` (string)
- `quality_score` (int 0-100)

**Missing utilities:**
- `classify_location(text) → str` — maps free text to Online/Hybrid/Offline
- `mark_stale(item, grace_days) → bool` — checks deadline vs today
- `quality_score(item) → int` — rates completeness 0-100
- `parse_prize(text) → str` — extracts "$34,500" from free text

---

## 4. THE 7 LOOPHOLES (Why Execution Was "Not Possible")

### Loop 1: Devfolio cards have almost no data
- Card HTML = `<a><h3>Title</h3></a>` — that's it
- No prize, no location, no tags, no organizer in card
- **FIX: Tier-2 detail scraping is mandatory for Devfolio**

### Loop 2: Devpost selectors are broken
- Prize extraction gets "$" instead of "$34,500"
- Tags extraction gets empty array instead of ["Machine Learning/AI", ...]
- Location extraction completely missing
- **FIX: Update selectors to match actual HTML structure**

### Loop 3: HackerEarth only shows 3 items
- Selector too specific — matches only above-the-fold cards
- No pagination/scroll mechanism
- No deadlines on listing page
- **FIX: Add scroll/pagination + Tier-2 for deadlines**

### Loop 4: Internshala items are silently dropped
- 75 items scraped → 0 in output
- merge_seeds.py requires non-empty deadline → all dropped
- **FIX: Allow empty deadlines in merge_seeds OR add Tier-2 deadline extraction**

### Loop 5: No location field in schema
- ScrapeItem has no `location` field
- Storage has no `location` field
- TypeScript types have no `location` field
- **FIX: Add field to all layers (Python → JSON → TypeScript → localStorage)**

### Loop 6: No staleness detection
- No code checks if deadline < today
- Stale entries accumulate in SEED_DATA
- No auto-completion of past events
- **FIX: Add staleness check to base.py + merge_seeds.py + validate-data.mjs**

### Loop 7: No quality scoring
- No way to rate scraped items by completeness
- Bad data (no deadline, no tags, no location) mixed with good data
- **FIX: Add quality_score() to base.py, use in filtering**

---

## 5. EXECUTION PLAN — FIXED ORDER

### Phase 0: Fix Critical Bugs (Must do first)

| # | File | Change | Why |
|---|------|--------|-----|
| 0a | `merge_seeds.py` | Remove the `if not deadline: skip` filter | Drops 75+ valid items |
| 0b | `devpost.py` | Fix prize selector: use `text_content()` not `.text` | Shows "$" instead of "$34,500" |
| 0c | `devpost.py` | Fix tags selector: use `t.attrib.get('title')` | Shows empty tags |
| 0d | `devpost.py` | Add location extraction from `.info-with-icon span` | No location data |
| 0e | `hackerearth.py` | Broaden selector or add scroll | Only 3 items |

### Phase 1: Add Missing Fields to Schema

| # | File | Change |
|---|------|--------|
| 1a | `base.py` | Add `location`, `prize_pool`, `participants`, `organizer`, `duration` to ScrapeItem |
| 1b | `base.py` | Add `classify_location(text)` helper |
| 1c | `base.py` | Add `quality_score(item)` helper |
| 1d | `opportunity.ts` | Add optional `location?`, `prize_pool?`, `participants?`, `organizer?` fields |
| 1e | `storage.ts` | Bump SEED_VERSION to 9 |

### Phase 2: Fix Each Scraper

| # | File | Changes |
|---|------|---------|
| 2a | `devpost.py` | Fix prize, tags, location selectors per HTML audit |
| 2b | `devfolio.py` | Add location extraction via page-level Online/Offline filter |
| 2c | `hackerearth.py` | Fix selector, add scroll for more items |
| 2d | `unstop.py` | Add eligibility parsing from tags, increase timeout |
| 2e | `internshala.py` | Fix deadline extraction, fix Unicode encoding |

### Phase 3: Build Tier-2 Enrichment

| # | File | Purpose |
|---|------|---------|
| 3a | `enrich.py` | Visit individual event pages for Devfolio/HackerEarth/Internshala |
| 3b | `quality.py` | Score each item 0-100 based on field completeness |
| 3c | `run_all.py` | Add `--detailed` flag, wire enrichment pipeline |

### Phase 4: Build Staleness & Cleanup

| # | File | Purpose |
|---|------|---------|
| 4a | `fix_stale.py` | One-time: mark stale entries in SEED_DATA as "Completed" |
| 4b | `merge_seeds.py` | Add auto-complete for stale items, add new fields |
| 4c | `validate-data.mjs` | Add staleness rules, quality warnings |

### Phase 5: Pipeline Integration

| # | File | Purpose |
|---|------|---------|
| 5a | `run_all.py` | Full pipeline: scrape → enrich → score → filter → output |
| 5b | `TASK_PLAN.md` | Live progress tracking |
| 5c | `package.json` | Add new npm scripts |
| 5d | Run full pipeline + verify |

---

## 6. DETAILED FIX SPECIFICATIONS

### Fix 0a: merge_seeds.py — Allow empty deadlines

```python
# CURRENT (BROKEN):
if not deadline:
    skipped += 1
    continue

# FIXED:
if not deadline:
    deadline = ""  # Keep item, just with empty deadline
    # Add a note that deadline is unknown
    if item.get("notes"):
        item["notes"] += " Deadline: unknown."
```

### Fix 0b: devpost.py — Prize extraction

```python
# CURRENT (BROKEN):
prize_el = card.css('.prize-amount')
prize = clean_text(prize_el[0].text if prize_el else "")

# FIXED:
prize_el = card.css('.prize-amount')
if prize_el:
    # text_content() gets "$34,500 in prizes" from nested spans
    prize = clean_text(prize_el[0].text_content())
else:
    prize = ""
```

### Fix 0c: devpost.py — Tags extraction

```python
# CURRENT (BROKEN):
tag_els = card.css('.theme-label')
tags = [clean_text(t.text) for t in tag_els if clean_text(t.text)]

# FIXED:
tag_els = card.css('.theme-label')
tags = []
for t in tag_els:
    # Get the title attribute which has clean tag name
    tag_name = t.attrib.get('title', '')
    if tag_name:
        tags.append(tag_name)
    else:
        # Fallback: get text content excluding checkmark icon
        tag_text = clean_text(str(t))
        if tag_text:
            tags.append(tag_text)
```

### Fix 0d: devpost.py — Location extraction

```python
# ADD after extracting status:
# Location: look for Online/Offline/Hybrid in info-with-icon
location_el = card.css('.info-with-icon span')
location = ""
for loc in location_el:
    loc_text = clean_text(loc.text)
    if loc_text.lower() in ('online', 'offline', 'hybrid', 'in person'):
        location = loc_text
        break
```

### Fix 1b: base.py — classify_location

```python
def classify_location(text: str) -> str:
    """Map free-text location to Online/Hybrid/Offline."""
    if not text:
        return ""
    text_lower = text.lower()
    online_keywords = ("online", "remote", "work from home", "wfh", "virtual", "anywhere")
    offline_keywords = ("offline", "in-person", "in person", "on-site", "onsite", "campus")
    hybrid_keywords = ("hybrid", "both", "online + in-person")
    
    for kw in hybrid_keywords:
        if kw in text_lower:
            return "Hybrid"
    for kw in online_keywords:
        if kw in text_lower:
            return "Online"
    for kw in offline_keywords:
        if kw in text_lower:
            return "Offline"
    return ""
```

### Fix 1c: base.py — quality_score

```python
def quality_score(item: "ScrapeItem") -> int:
    """Rate item completeness 0-100."""
    score = 0
    if item.deadline: score += 25
    if item.location: score += 15
    if item.prize_pool: score += 15
    if item.participants: score += 10
    if item.tags: score += 10
    if item.eligibility and "Check " not in item.eligibility: score += 10
    if item.notes and "Source:" not in item.notes: score += 10
    if item.link and item.link.startswith("http"): score += 5
    return score
```

### Fix 2a: devpost.py — Full selector update

The Devpost card HTML structure (verified by live inspection):
```
div.hackathon-tile
  a.tile-anchor[href]
    div.main-content
      h3 mb-4                              → TITLE
      div.hackathon-status                  → STATUS (Upcoming/Live/etc)
      div.info-with-icon > span             → LOCATION (Online/Offline)
    div.side-info
      div.host > span.host-label            → HOST
      div.submission-period                  → DATE RANGE
      div.themes > span.theme-label          → TAGS (use title attr)
      div.prize > span.prize-amount          → PRIZE (use text_content())
      div.participants > strong              → PARTICIPANTS
```

---

## 7. MANUS-STYLE PROGRESS TRACKER

### Current State
```
[ ] Phase 0: Fix critical bugs
    [ ] 0a: merge_seeds.py deadline filter
    [ ] 0b: devpost.py prize selector
    [ ] 0c: devpost.py tags selector
    [ ] 0d: devpost.py location extraction
    [ ] 0e: hackerearth.py selector broadening
[ ] Phase 1: Add missing fields
    [ ] 1a: base.py new fields
    [ ] 1b: base.py classify_location
    [ ] 1c: base.py quality_score
    [ ] 1d: opportunity.ts types
    [ ] 1e: storage.ts version bump
[ ] Phase 2: Fix each scraper
    [ ] 2a: devpost.py full fix
    [ ] 2b: devfolio.py location
    [ ] 2c: hackerearth.py fix
    [ ] 2d: unstop.py improvements
    [ ] 2e: internshala.py fix
[ ] Phase 3: Tier-2 enrichment
    [ ] 3a: enrich.py
    [ ] 3b: quality.py
    [ ] 3c: run_all.py pipeline
[ ] Phase 4: Staleness & cleanup
    [ ] 4a: fix_stale.py
    [ ] 4b: merge_seeds.py improvements
    [ ] 4c: validate-data.mjs rules
[ ] Phase 5: Integration
    [ ] 5a: run_all.py full pipeline
    [ ] 5b: TASK_PLAN.md updates
    [ ] 5c: package.json scripts
    [ ] 5d: Verify end-to-end
```

---

## 8. DATA FLOW — COMPLETE PATH

```
Source websites
    │
    ▼
[Scraper Layer] ─── devfolio.py / devpost.py / unstop.py / hackerearth.py / internshala.py
    │                   Each produces list[ScrapeItem]
    │                   ScrapeItem now has: location, prize_pool, participants, organizer
    ▼
[Quality Scoring] ─── quality_score(item) → 0-100
    │                   Items below 20 get logged as warnings
    ▼
[Staleness Detection] ─── mark_stale(item) → bool
    │                       Items >30 days past deadline get flagged
    ▼
[Deduplication] ─── deduplicate(items) by fingerprint
    │
    ▼
[Enrichment (Optional)] ─── enrich.py visits detail pages
    │                       Fills in: deadline, location, prize, eligibility
    │                       Only for items with quality_score < 50
    ▼
[Output] ─── data/scraped_opportunities.json
    │
    ▼
[Merge Layer] ─── merge_seeds.py
    │               Dedup against SEED_DATA by title + link
    │               Auto-complete stale entries
    │               Generate TypeScript entries with new fields
    ▼
[Validation] ─── validate-data.mjs
    │               Schema validation
    │               Staleness errors
    │               Quality warnings
    │               Link checking (optional)
    ▼
[Storage] ─── storage.ts
    │           SEED_DATA array
    │           Version-gated merge on load
    ▼
[UI] ─── React components
            Dashboard, Weekly Review, Stats
            Filter by location, quality, staleness
```

---

## 9. OPEN QUESTIONS

1. **Devfolio Tier-2**: Should we scrape all 25 detail pages (adds ~2 min) or skip detail for Devfolio?
2. **HackerEarth pagination**: Should we scroll to load all 61 cards or accept 3?
3. **Internshala deadlines**: Accept empty deadlines or Tier-2 scrape all 75 pages?
4. **Quality threshold**: What minimum quality score should trigger a warning?
5. **Staleness grace period**: 7 days? 14 days? 30 days?

---

*This document is the single source of truth for the scraper system. Update after each phase completion.*
