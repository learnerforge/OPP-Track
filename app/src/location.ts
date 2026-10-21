/**
 * Location parsing + proximity for the events page.
 *
 * The scraped `location` field is free text ("Bengaluru, India", "Online",
 * "Berlin", "Remote"). To sort by distance we need coordinates. There are two
 * sources, tried in this order:
 *
 *   1. **Real coordinates from the scraper** — `public/data/locations.json`,
 *      written by `scripts/scrapers/geocode.py`, which geocodes each distinct
 *      location with OpenStreetMap Nominatim at scrape time. This places actual
 *      venues ("IIIT Delhi" -> the campus) and small towns a table never could.
 *   2. **A built-in gazetteer** (below) as the fallback, for anything the
 *      geocoder missed or has not seen yet — for example a brand-new location
 *      before the next scrape, or when the side file is absent in local dev.
 *
 * Neither source is fetched from the network at request time: rung 1 is a
 * static asset and rung 2 is compiled in. So a page load never waits on a
 * geocoding service, and there is no API key to leak.
 *
 * Unresolvable or remote/online locations get no coordinates and therefore
 * always sort last — the same "no value sorts last" rule the other keys use.
 */

/** Latitude/longitude in decimal degrees. */
export interface Coord {
  lat: number;
  lon: number;
}

/**
 * Normalise a location string for comparison: lowercase, strip accents and
 * punctuation. "Bengaluru, India" and "bengaluru india" must collide.
 */
function norm(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s,]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Terms that mean "no physical place" — never get coordinates. */
const NON_PHYSICAL = new Set([
  "online",
  "remote",
  "virtual",
  "anywhere",
  "worldwide",
  "global",
  "hybrid",
  "virtual event",
  "online event",
  "remote friendly",
  "work from home",
  "wfh",
  // Scraper artefacts that are not places at all. Left unplaced so they never
  // pollute a distance sort or claim a false "nearest" position.
  "various",
  "various us",
  "offline",
  "in person",
  "prize",
  "registering",
  "upcoming",
  "tbd",
  "n a",
  "na",
]);

/** True when the location string describes an online/unlocated event. */
export function isNonPhysical(location?: string): boolean {
  if (!location) return true;
  const n = norm(location);
  if (!n) return true;
  if (NON_PHYSICAL.has(n)) return true;
  // "Various (US)" normalises to "various us"; strip a parenthesised suffix.
  const bare = n.replace(/\s*\([^)]*\)\s*/g, " ").replace(/\s+/g, " ").trim();
  if (NON_PHYSICAL.has(bare)) return true;
  // "Online / Remote", "Virtual (worldwide)" etc.
  return n
    .split(/[,\s/|]+/)
    .filter(Boolean)
    .every((part) => NON_PHYSICAL.has(part));
}

/**
 * Gazetteer of cities that appear in the dataset, keyed by canonical name.
 * Indian cities carry state context because several names repeat.
 */
const CITIES: Record<string, Coord> = {
  // ── India ────────────────────────────────────────────────────────────────
  bengaluru: { lat: 12.9716, lon: 77.5946 },
  bangalore: { lat: 12.9716, lon: 77.5946 },
  delhi: { lat: 28.6139, lon: 77.209 },
  "new delhi": { lat: 28.6139, lon: 77.209 },
  mumbai: { lat: 19.076, lon: 72.8777 },
  bombay: { lat: 19.076, lon: 72.8777 },
  pune: { lat: 18.5204, lon: 73.8567 },
  hyderabad: { lat: 17.385, lon: 78.4867 },
  chennai: { lat: 13.0827, lon: 80.2707 },
  madras: { lat: 13.0827, lon: 80.2707 },
  kolkata: { lat: 22.5726, lon: 88.3639 },
  calcutta: { lat: 22.5726, lon: 88.3639 },
  noida: { lat: 28.5355, lon: 77.391 },
  gurugram: { lat: 28.4595, lon: 77.0266 },
  gurgaon: { lat: 28.4595, lon: 77.0266 },
  kochi: { lat: 9.9312, lon: 76.2673 },
  cochin: { lat: 9.9312, lon: 76.2673 },
  jaipur: { lat: 26.9124, lon: 75.7873 },
  ahmedabad: { lat: 23.0225, lon: 72.5714 },
  indore: { lat: 22.7196, lon: 75.8577 },
  kozhikode: { lat: 11.2588, lon: 75.7804 },
  calicut: { lat: 11.2588, lon: 75.7804 },
  lucknow: { lat: 26.8467, lon: 80.9462 },
  nagpur: { lat: 21.1458, lon: 79.0882 },
  coimbatore: { lat: 11.0168, lon: 76.9558 },
  chandigarh: { lat: 30.7333, lon: 76.7794 },
  bhopal: { lat: 23.2599, lon: 77.4126 },
  goa: { lat: 15.2993, lon: 74.124 },
  panaji: { lat: 15.4909, lon: 73.8278 },
  dehradun: { lat: 30.3165, lon: 78.0322 },
  ghaziabad: { lat: 28.6692, lon: 77.4538 },
  kanpur: { lat: 26.4499, lon: 80.3319 },
  thane: { lat: 19.2183, lon: 72.9781 },
  visakhapatnam: { lat: 17.6868, lon: 83.2185 },
  vizag: { lat: 17.6868, lon: 83.2185 },
  trivandrum: { lat: 8.5241, lon: 76.9366 },
  thiruvananthapuram: { lat: 8.5241, lon: 76.9366 },
  mysuru: { lat: 12.2958, lon: 76.6394 },
  mysore: { lat: 12.2958, lon: 76.6394 },
  mangaluru: { lat: 12.9141, lon: 74.856 },
  mangalore: { lat: 12.9141, lon: 74.856 },
  surat: { lat: 21.1702, lon: 72.8311 },
  vadodara: { lat: 22.3072, lon: 73.1812 },
  nashik: { lat: 19.9975, lon: 73.7898 },
  aurangabad: { lat: 19.8762, lon: 75.3433 },
  patna: { lat: 25.5941, lon: 85.1376 },
  ranchi: { lat: 23.3441, lon: 85.3096 },
  bhubaneswar: { lat: 20.2961, lon: 85.8245 },
  guwahati: { lat: 26.1445, lon: 91.7362 },
  amritsar: { lat: 31.634, lon: 74.8723 },
  ludhiana: { lat: 30.901, lon: 75.8573 },
  varanasi: { lat: 25.3176, lon: 82.9739 },
  agra: { lat: 27.1767, lon: 78.0081 },
  meerut: { lat: 28.9845, lon: 77.7064 },
  rajkot: { lat: 22.3039, lon: 70.8022 },
  madurai: { lat: 9.9252, lon: 78.1198 },
  tiruchirappalli: { lat: 10.7905, lon: 78.7047 },
  salem: { lat: 11.6643, lon: 78.146 },
  warangal: { lat: 17.9689, lon: 79.5941 },
  vijayawada: { lat: 16.5062, lon: 80.648 },
  guntur: { lat: 16.3067, lon: 80.4365 },
  tirupati: { lat: 13.6288, lon: 79.4192 },
  jodhpur: { lat: 26.2389, lon: 73.0243 },
  udaipur: { lat: 24.5854, lon: 73.7125 },
  kota: { lat: 25.2138, lon: 75.8648 },
  raipur: { lat: 21.2514, lon: 81.6296 },
  jabalpur: { lat: 23.1815, lon: 79.9864 },
  gwalior: { lat: 26.2183, lon: 78.1828 },
  jalandhar: { lat: 31.326, lon: 75.5762 },
  srinagar: { lat: 34.0837, lon: 74.7973 },
  shimla: { lat: 31.1048, lon: 77.1734 },
  siliguri: { lat: 26.7271, lon: 88.3953 },
  // ── Global tech hubs ────────────────────────────────────────────────────
  "san francisco": { lat: 37.7749, lon: -122.4194 },
  "bay area": { lat: 37.7749, lon: -122.4194 },
  "silicon valley": { lat: 37.3875, lon: -122.0575 },
  "palo alto": { lat: 37.4419, lon: -122.143 },
  "mountain view": { lat: 37.3861, lon: -122.0839 },
  "los angeles": { lat: 34.0522, lon: -118.2437 },
  "new york": { lat: 40.7128, lon: -74.006 },
  nyc: { lat: 40.7128, lon: -74.006 },
  boston: { lat: 42.3601, lon: -71.0589 },
  seattle: { lat: 47.6062, lon: -122.3321 },
  austin: { lat: 30.2672, lon: -97.7431 },
  chicago: { lat: 41.8781, lon: -87.6298 },
  denver: { lat: 39.7392, lon: -104.9903 },
  toronto: { lat: 43.6532, lon: -79.3832 },
  vancouver: { lat: 49.2827, lon: -123.1207 },
  london: { lat: 51.5074, lon: -0.1278 },
  cambridge: { lat: 52.2053, lon: 0.1218 },
  oxford: { lat: 51.752, lon: -1.2577 },
  manchester: { lat: 53.4808, lon: -2.2426 },
  edinburgh: { lat: 55.9533, lon: -3.1883 },
  dublin: { lat: 53.3498, lon: -6.2603 },
  berlin: { lat: 52.52, lon: 13.405 },
  munich: { lat: 48.1351, lon: 11.582 },
  hamburg: { lat: 53.5511, lon: 9.9937 },
  paris: { lat: 48.8566, lon: 2.3522 },
  amsterdam: { lat: 52.3676, lon: 4.9041 },
  brussels: { lat: 50.8503, lon: 4.3517 },
  zurich: { lat: 47.3769, lon: 8.5417 },
  geneva: { lat: 46.2044, lon: 6.1432 },
  vienna: { lat: 48.2082, lon: 16.3738 },
  stockholm: { lat: 59.3293, lon: 18.0686 },
  oslo: { lat: 59.9139, lon: 10.7522 },
  copenhagen: { lat: 55.6761, lon: 12.5683 },
  helsinki: { lat: 60.1699, lon: 24.9384 },
  madrid: { lat: 40.4168, lon: -3.7038 },
  barcelona: { lat: 41.3874, lon: 2.1686 },
  lisbon: { lat: 38.7223, lon: -9.1393 },
  rome: { lat: 41.9028, lon: 12.4964 },
  milan: { lat: 45.4642, lon: 9.19 },
  prague: { lat: 50.0755, lon: 14.4378 },
  warsaw: { lat: 52.2297, lon: 21.0122 },
  budapest: { lat: 47.4979, lon: 19.0402 },
  athens: { lat: 37.9838, lon: 23.7275 },
  istanbul: { lat: 41.0082, lon: 28.9784 },
  moscow: { lat: 55.7558, lon: 37.6173 },
  dubai: { lat: 25.2048, lon: 55.2708 },
  "abu dhabi": { lat: 24.4539, lon: 54.3773 },
  doha: { lat: 25.2854, lon: 51.531 },
  riyadh: { lat: 24.7136, lon: 46.6753 },
  "tel aviv": { lat: 32.0853, lon: 34.7818 },
  singapore: { lat: 1.3521, lon: 103.8198 },
  tokyo: { lat: 35.6762, lon: 139.6503 },
  osaka: { lat: 34.6937, lon: 135.5023 },
  seoul: { lat: 37.5665, lon: 126.978 },
  beijing: { lat: 39.9042, lon: 116.4074 },
  shanghai: { lat: 31.2304, lon: 121.4737 },
  shenzhen: { lat: 22.5431, lon: 114.0579 },
  hangzhou: { lat: 30.2741, lon: 120.1551 },
  "hong kong": { lat: 22.3193, lon: 114.1694 },
  taipei: { lat: 25.033, lon: 121.5654 },
  bangkok: { lat: 13.7563, lon: 100.5018 },
  jakarta: { lat: -6.2088, lon: 106.8456 },
  "kuala lumpur": { lat: 3.139, lon: 101.6869 },
  manila: { lat: 14.5995, lon: 120.9842 },
  hanoi: { lat: 21.0278, lon: 105.8342 },
  "ho chi minh": { lat: 10.8231, lon: 106.6297 },
  sydney: { lat: -33.8688, lon: 151.2093 },
  melbourne: { lat: -37.8136, lon: 144.9631 },
  brisbane: { lat: -27.4698, lon: 153.0251 },
  perth: { lat: -31.9505, lon: 115.8605 },
  auckland: { lat: -36.8485, lon: 174.7633 },
  wellington: { lat: -41.2866, lon: 174.7756 },
  "sao paulo": { lat: -23.5505, lon: -46.6333 },
  "rio de janeiro": { lat: -22.9068, lon: -43.1729 },
  "buenos aires": { lat: -34.6037, lon: -58.3816 },
  santiago: { lat: -33.4489, lon: -70.6693 },
  bogota: { lat: 4.711, lon: -74.0721 },
  lima: { lat: -12.0464, lon: -77.0428 },
  "mexico city": { lat: 19.4326, lon: -99.1332 },
  nairobi: { lat: -1.2921, lon: 36.8219 },
  lagos: { lat: 6.5244, lon: 3.3792 },
  accra: { lat: 5.6037, lon: -0.187 },
  "cape town": { lat: -33.9249, lon: 18.4241 },
  johannesburg: { lat: -26.2041, lon: 28.0473 },
  cairo: { lat: 30.0444, lon: 31.2357 },
  casablanca: { lat: 33.5731, lon: -7.5898 },
  // ── Additional cities observed in the catalog ───────────────────────────
  luxembourg: { lat: 49.6116, lon: 6.1319 },
  cincinnati: { lat: 39.1031, lon: -84.512 },
  cleveland: { lat: 41.4993, lon: -81.6944 },
  columbus: { lat: 39.9612, lon: -82.9988 },
  atlanta: { lat: 33.749, lon: -84.388 },
  montreal: { lat: 45.5019, lon: -73.5674 },
  ottawa: { lat: 45.4215, lon: -75.6972 },
  calgary: { lat: 51.0447, lon: -114.0719 },
  mississauga: { lat: 43.589, lon: -79.6441 },
  kitchener: { lat: 43.4516, lon: -80.4925 },
  waterloo: { lat: 43.4643, lon: -80.5204 },
  hamilton: { lat: 43.2557, lon: -79.8711 },
  winnipeg: { lat: 49.8951, lon: -97.1384 },
  dallas: { lat: 32.7767, lon: -96.797 },
  houston: { lat: 29.7604, lon: -95.3698 },
  "san diego": { lat: 32.7157, lon: -117.1611 },
  "san jose": { lat: 37.3382, lon: -121.8863 },
  sunnyvale: { lat: 37.3688, lon: -122.0363 },
  redmond: { lat: 47.674, lon: -122.1215 },
  bellevue: { lat: 47.6101, lon: -122.2015 },
  portland: { lat: 45.5152, lon: -122.6784 },
  pittsburgh: { lat: 40.4406, lon: -79.9959 },
  raleigh: { lat: 35.7796, lon: -78.6382 },
  durham: { lat: 35.994, lon: -78.8986 },
  reston: { lat: 38.9586, lon: -77.357 },
  richardson: { lat: 32.9483, lon: -96.7299 },
  "ann arbor": { lat: 42.2808, lon: -83.743 },
  boulder: { lat: 40.015, lon: -105.2705 },
  goleta: { lat: 34.4358, lon: -119.8276 },
  "santa cruz": { lat: 36.9741, lon: -122.0308 },
  "washington dc": { lat: 38.9072, lon: -77.0369 },
  "washington d c": { lat: 38.9072, lon: -77.0369 },
  "st louis": { lat: 38.627, lon: -90.1994 },
  minneapolis: { lat: 44.9778, lon: -93.265 },
  detroit: { lat: 42.3314, lon: -83.0458 },
  philadelphia: { lat: 39.9526, lon: -75.1652 },
  phoenix: { lat: 33.4484, lon: -112.074 },
  "salt lake city": { lat: 40.7608, lon: -111.891 },
  lehi: { lat: 40.3916, lon: -111.8508 },
  boise: { lat: 43.615, lon: -116.2023 },
  omaha: { lat: 41.2565, lon: -95.9345 },
  wichita: { lat: 37.6872, lon: -97.3301 },
  louisville: { lat: 38.2527, lon: -85.7585 },
  greenville: { lat: 34.8526, lon: -82.394 },
  melbourne_fl: { lat: 28.0836, lon: -80.6081 },
  huntsville: { lat: 34.7304, lon: -86.5861 },
  honolulu: { lat: 21.3069, lon: -157.8583 },
  "el paso": { lat: 31.7619, lon: -106.485 },
  "fort worth": { lat: 32.7555, lon: -97.3308 },
  "fort wayne": { lat: 41.0793, lon: -85.1394 },
  "west lafayette": { lat: 40.4259, lon: -86.9081 },
  "college station": { lat: 30.628, lon: -96.3344 },
  knoxville: { lat: 35.9606, lon: -83.9207 },
  nashville: { lat: 36.1627, lon: -86.7816 },
  charlotte: { lat: 35.2271, lon: -80.8431 },
  orlando: { lat: 28.5383, lon: -81.3792 },
  tampa: { lat: 27.9506, lon: -82.4572 },
  clemson: { lat: 34.6834, lon: -82.8374 },
  urbana: { lat: 40.1106, lon: -88.2073 },
  madison: { lat: 43.0731, lon: -89.4012 },
  milwaukee: { lat: 43.0389, lon: -87.9065 },
  "la crosse": { lat: 43.8014, lon: -91.2396 },
  "oak creek": { lat: 42.8858, lon: -87.8631 },
  waukesha: { lat: 43.0117, lon: -88.2315 },
  dayton: { lat: 39.7589, lon: -84.1916 },
  toledo: { lat: 41.6528, lon: -83.5379 },
  akron: { lat: 41.0814, lon: -81.519 },
  mentor: { lat: 41.6662, lon: -81.3396 },
  lorain: { lat: 41.4528, lon: -82.1824 },
  delaware_oh: { lat: 40.2987, lon: -83.0682 },
  mansfield_oh: { lat: 40.7584, lon: -82.5154 },
  limerick: { lat: 52.6638, lon: -8.6267 },
  bucharest: { lat: 44.4268, lon: 26.1025 },
  timisoara: { lat: 45.7489, lon: 21.2087 },
  espoo: { lat: 60.2055, lon: 24.6559 },
  turku: { lat: 60.4518, lon: 22.2666 },
  birmingham: { lat: 52.4862, lon: -1.8904 },
  bristol: { lat: 51.4545, lon: -2.5879 },
  glasgow: { lat: 55.8642, lon: -4.2518 },
  lyon: { lat: 45.764, lon: 4.8357 },
  toulouse: { lat: 43.6047, lon: 1.4442 },
  "clichy": { lat: 48.9044, lon: 2.3064 },
  lleida: { lat: 41.6176, lon: 0.62 },
  "san fernando de henares": { lat: 40.4475, lon: -3.5342 },
  bad_hersfeld: { lat: 50.8667, lon: 9.7 },
  "luxembourg city": { lat: 49.6116, lon: 6.1319 },
  york: { lat: 53.9599, lon: -1.0873 },
  leeds: { lat: 53.8008, lon: -1.5491 },
  liverpool: { lat: 53.4084, lon: -2.9916 },
  peterborough: { lat: 52.5695, lon: -0.2405 },
  riyadh_sa: { lat: 24.7136, lon: 46.6753 },
  jeddah: { lat: 21.4858, lon: 39.1925 },
  haifa: { lat: 32.794, lon: 34.9896 },
  taipei_city: { lat: 25.033, lon: 121.5654 },
  "new taipei": { lat: 25.0114, lon: 121.4618 },
  banqiao: { lat: 25.0114, lon: 121.4618 },
  merida: { lat: 20.9674, lon: -89.5926 },
  leon: { lat: 21.125, lon: -101.686 },
  apodaca: { lat: 25.7791, lon: -100.1884 },
  cali: { lat: 3.4516, lon: -76.532 },
  belo_horizonte: { lat: -19.9167, lon: -43.9345 },
  wellington_nz: { lat: -41.2866, lon: 174.7756 },
  "horsley park": { lat: -33.8583, lon: 150.8553 },
  fresno: { lat: 36.7378, lon: -119.7871 },
  "las vegas": { lat: 36.1699, lon: -115.1398 },
  // Indian cities not yet listed
  amroha: { lat: 28.9044, lon: 78.4669 },
  bilaspur: { lat: 22.0797, lon: 82.1409 },
  haldwani: { lat: 29.2183, lon: 79.513 },
  kharar: { lat: 30.7457, lon: 76.6465 },
  sonipat: { lat: 28.9931, lon: 77.0151 },
  patiala: { lat: 30.3398, lon: 76.3869 },
  vellore: { lat: 12.9165, lon: 79.1325 },
  myladi: { lat: 8.2017, lon: 77.5408 },
  "new chandigarh": { lat: 30.7667, lon: 76.8 },
};

/** Country / region centroids, used when no city matches. */
const COUNTRIES: Record<string, Coord> = {
  india: { lat: 20.5937, lon: 78.9629 },
  usa: { lat: 39.8283, lon: -98.5795 },
  "united states": { lat: 39.8283, lon: -98.5795 },
  "united states of america": { lat: 39.8283, lon: -98.5795 },
  america: { lat: 39.8283, lon: -98.5795 },
  canada: { lat: 56.1304, lon: -106.3468 },
  uk: { lat: 55.3781, lon: -3.436 },
  "united kingdom": { lat: 55.3781, lon: -3.436 },
  england: { lat: 52.3555, lon: -1.1743 },
  scotland: { lat: 56.4907, lon: -4.2026 },
  ireland: { lat: 53.1424, lon: -7.6921 },
  germany: { lat: 51.1657, lon: 10.4515 },
  france: { lat: 46.2276, lon: 2.2137 },
  netherlands: { lat: 52.1326, lon: 5.2913 },
  belgium: { lat: 50.5039, lon: 4.4699 },
  switzerland: { lat: 46.8182, lon: 8.2275 },
  austria: { lat: 47.5162, lon: 14.5501 },
  spain: { lat: 40.4637, lon: -3.7492 },
  portugal: { lat: 39.3999, lon: -8.2245 },
  italy: { lat: 41.8719, lon: 12.5674 },
  poland: { lat: 51.9194, lon: 19.1451 },
  sweden: { lat: 60.1282, lon: 18.6435 },
  norway: { lat: 60.472, lon: 8.4689 },
  denmark: { lat: 56.2639, lon: 9.5018 },
  finland: { lat: 61.9241, lon: 25.7482 },
  greece: { lat: 39.0742, lon: 21.8243 },
  turkey: { lat: 38.9637, lon: 35.2433 },
  russia: { lat: 61.524, lon: 105.3188 },
  ukraine: { lat: 48.3794, lon: 31.1656 },
  czechia: { lat: 49.8175, lon: 15.473 },
  "czech republic": { lat: 49.8175, lon: 15.473 },
  hungary: { lat: 47.1625, lon: 19.5033 },
  romania: { lat: 45.9432, lon: 24.9668 },
  uae: { lat: 23.4241, lon: 53.8478 },
  "united arab emirates": { lat: 23.4241, lon: 53.8478 },
  "saudi arabia": { lat: 23.8859, lon: 45.0792 },
  qatar: { lat: 25.3548, lon: 51.1839 },
  israel: { lat: 31.0461, lon: 34.8516 },
  egypt: { lat: 26.8206, lon: 30.8025 },
  nigeria: { lat: 9.082, lon: 8.6753 },
  kenya: { lat: -0.0236, lon: 37.9062 },
  ghana: { lat: 7.9465, lon: -1.0232 },
  "south africa": { lat: -30.5595, lon: 22.9375 },
  morocco: { lat: 31.7917, lon: -7.0926 },
  china: { lat: 35.8617, lon: 104.1954 },
  japan: { lat: 36.2048, lon: 138.2529 },
  "south korea": { lat: 35.9078, lon: 127.7669 },
  korea: { lat: 35.9078, lon: 127.7669 },
  singapore_country: { lat: 1.3521, lon: 103.8198 },
  malaysia: { lat: 4.2105, lon: 101.9758 },
  indonesia: { lat: -0.7893, lon: 113.9213 },
  thailand: { lat: 15.87, lon: 100.9925 },
  vietnam: { lat: 14.0583, lon: 108.2772 },
  philippines: { lat: 12.8797, lon: 121.774 },
  australia: { lat: -25.2744, lon: 133.7751 },
  "new zealand": { lat: -40.9006, lon: 174.886 },
  brazil: { lat: -14.235, lon: -51.9253 },
  argentina: { lat: -38.4161, lon: -63.6167 },
  chile: { lat: -35.6751, lon: -71.543 },
  colombia: { lat: 4.5709, lon: -74.2973 },
  peru: { lat: -9.19, lon: -75.0152 },
  mexico: { lat: 23.6345, lon: -102.5528 },
  europe: { lat: 50.0, lon: 10.0 },
  asia: { lat: 30.0, lon: 100.0 },
  africa: { lat: 5.0, lon: 20.0 },
};

/** Aliases that map a scraped label onto a gazetteer key. */
const ALIASES: Record<string, string> = {
  blr: "bengaluru",
  bombay: "mumbai",
  "delhi ncr": "delhi",
  ncr: "delhi",
  "new delhi": "delhi",
  gurgaon: "gurugram",
  cochin: "kochi",
  calicut: "kozhikode",
  mysore: "mysuru",
  mangalore: "mangaluru",
  vizag: "visakhapatnam",
  "thiruvananthapuram": "trivandrum",
  madras: "chennai",
  calcutta: "kolkata",
  "bengaluru urban": "bengaluru",
  // ── Country / province aliases seen in the scraped location strings ──────
  us: "usa",
  "u.s.": "usa",
  "u.s.a.": "usa",
  "united states of america": "united states",
  "great britain": "united kingdom",
  britain: "united kingdom",
  holland: "netherlands",
  "the netherlands": "netherlands",
  emirates: "uae",
  uae: "uae",
  // ISO-3166 alpha-2 codes, as scraped in "City, CC" form.
  in: "india",
  gb: "united kingdom",
  uk: "united kingdom",
  ca: "canada",
  au: "australia",
  nz: "new zealand",
  de: "germany",
  fr: "france",
  nl: "netherlands",
  be: "belgium",
  ch: "switzerland",
  at: "austria",
  es: "spain",
  pt: "portugal",
  it: "italy",
  pl: "poland",
  se: "sweden",
  no: "norway",
  dk: "denmark",
  fi: "finland",
  gr: "greece",
  tr: "turkey",
  ru: "russia",
  ua: "ukraine",
  cz: "czechia",
  hu: "hungary",
  ro: "romania",
  il: "israel",
  eg: "egypt",
  ng: "nigeria",
  ke: "kenya",
  gh: "ghana",
  za: "south africa",
  ma: "morocco",
  cn: "china",
  jp: "japan",
  kr: "south korea",
  sg: "singapore",
  my: "malaysia",
  id: "indonesia",
  th: "thailand",
  vn: "vietnam",
  ph: "philippines",
  br: "brazil",
  ar: "argentina",
  cl: "chile",
  co: "colombia",
  pe: "peru",
  mx: "mexico",
  // ── Indian states / union territories (fall back to the India centroid) ──
  karnataka: "india",
  maharashtra: "india",
  "tamil nadu": "india",
  telangana: "india",
  "andhra pradesh": "india",
  kerala: "india",
  "uttar pradesh": "india",
  "madhya pradesh": "india",
  rajasthan: "india",
  gujarat: "india",
  "west bengal": "india",
  punjab: "india",
  haryana: "india",
  bihar: "india",
  jharkhand: "india",
  odisha: "india",
  orissa: "india",
  assam: "india",
  chhattisgarh: "india",
  uttarakhand: "india",
  "himachal pradesh": "india",
  goa_state: "india",
  "jammu and kashmir": "india",
  // ── US states (fall back to the USA centroid) ───────────────────────────
  california: "usa",
  "new york state": "usa",
  illinois: "usa",
  "new jersey": "usa",
  texas: "usa",
  washington: "usa",
  massachusetts: "usa",
  michigan: "usa",
  florida: "usa",
  georgia: "usa",
  virginia: "usa",
  ohio: "usa",
  pennsylvania: "usa",
  // ── Canadian provinces ──────────────────────────────────────────────────
  ontario: "canada",
  quebec: "canada",
  alberta: "canada",
  "british columbia": "canada",
  manitoba: "canada",
  saskatchewan: "canada",
  // ── Australian states ───────────────────────────────────────────────────
  "new south wales": "australia",
  victoria: "australia",
  queensland: "australia",
};

/**
 * US state abbreviations, which are NOT country aliases.
 *
 * These are deliberately kept out of `ALIASES`: `CA`, `DE`, `ID`, `IL`, `IN`
 * and `CO` are simultaneously ISO country codes (Canada, Germany, Indonesia,
 * Israel, India, Colombia) and US state codes (California, Delaware, Idaho,
 * Illinois, Indiana, Colorado). A bare code is therefore meaningless, and the
 * only safe reading depends on where it sits: `"Calgary, CA"` and
 * `"Cincinnati, OH"` put the state *last*, after a city, whereas `"MX, DIF,
 * Mexico City"` and `"US, WA, Seattle"` put the country *first*. Position, not
 * value, decides — so the codes are resolved by the ladder below rather than
 * by a flat lookup table.
 */
const US_STATES = new Set([
  "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
  "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
  "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
  "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
  "wi", "wy", "dc",
]);

/**
 * Canadian province abbreviations, which likewise clash with country codes
 * (`ON`, `BC`, `AB`, `QC`, `MB`, `SK`, `NS`, `NB`, `NL`).
 */
const CA_PROVINCES = new Set(["on", "bc", "ab", "qc", "mb", "sk", "ns", "nb", "nl", "pe", "yt", "nt", "nu"]);

/**
 * Resolve a location string to coordinates.
 *
 * Returns null for online/remote/unlocated strings and for anything the
 * gazetteer cannot place — callers treat null as "sorts last".
 *
 * Scraped locations come in several shapes and each is tried in turn:
 *   "Bengaluru, India"          city + country
 *   "Cincinnati, OH"            city + US state code (state resolves to US)
 *   "US, WA, Seattle"           country code, region code, city
 *   "Various" / "Offline"       not a place at all
 */
export function geocode(location?: string): Coord | null {
  if (isNonPhysical(location)) return null;
  const n = norm(location!);

  const lookup = (key: string): Coord | null => {
    const canonical = ALIASES[key] ?? key;
    return CITIES[canonical] ?? COUNTRIES[canonical] ?? null;
  };

  const parts = n.split(",").map((p) => p.trim()).filter(Boolean);

  // 1. whole string
  const whole = lookup(n);
  if (whole) return whole;

  // 2. the part before the first comma is usually the locality
  if (parts.length > 1) {
    const byHead = lookup(parts[0]);
    if (byHead) return byHead;
  }

  // 3. "CC, REGION, City" — the FIRST segment is a country code, and the LAST
  //    is usually the city (e.g. "MX, DIF, Mexico City"). Try the tail as a
  //    city before falling back to the country centroid, so Mexico City beats
  //    the Mexico centroid. This also covers "US, WA, Seattle".
  if (parts.length >= 3) {
    const byTail = lookup(parts[parts.length - 1]);
    if (byTail) return byTail;
    const byFirst = lookup(parts[0]);
    if (byFirst) return byFirst;
  }

  // 4. longest alias contained anywhere (avoids "delhi" beating "new delhi")
  const candidates = [...Object.keys(CITIES), ...Object.keys(COUNTRIES)].sort(
    (a, b) => b.length - a.length,
  );
  for (const key of candidates) {
    if (key.length < 5) continue; // skip short codes in substring mode
    if (n.includes(key)) {
      const hit = lookup(key);
      if (hit) return hit;
    }
  }

  // 5. trailing 2-letter segment — "Cincinnati, OH", "Calgary, CA". Only read
  //    this way when a comma separates it, and let a known city in the head
  //    win first (step 2 above already tried that). US state codes take
  //    precedence over country codes here because the head already told us
  //    the continent — "Calgary, CA" is California's code, but Calgary is in
  //    Canada, and the Canadian province set below is checked in turn.
  if (parts.length >= 2) {
    const tail = parts[parts.length - 1];
    if (tail.length === 2) {
      const headIsCanadianCity = [
        "calgary",
        "toronto",
        "vancouver",
        "montreal",
        "ottawa",
        "winnipeg",
        "edmonton",
        "mississauga",
      ].includes(parts[0]);
      if (CA_PROVINCES.has(tail) || (US_STATES.has(tail) && headIsCanadianCity)) {
        return COUNTRIES.canada;
      }
      if (US_STATES.has(tail)) return COUNTRIES.usa;
      // A bare country code in the tail ("London, UK", "Berlin, DE").
      const byTail = lookup(tail);
      if (byTail) return byTail;
    }
  }

  // 6. trailing region — "Someplace, Karnataka, India" -> India centroid
  for (let i = parts.length - 1; i >= 1; i--) {
    const hit = lookup(parts[i]);
    if (hit) return hit;
  }

  return null;
}

/**
 * Real coordinates scraped from the dataset, keyed by the exact location
 * string (see scripts/scrapers/geocode.py). Populated by `hydrateCoords`.
 */
let scrapedCoords: Record<string, Coord> = {};
let coordsLoaded = false;

/** True once the real-coordinate side file has been read (or found absent). */
export function coordsReady(): boolean {
  return coordsLoaded;
}

/**
 * Load `public/data/locations.json` — the scrape-time geocoding results.
 *
 * Safe to call more than once and safe to fail: a missing or malformed file
 * simply leaves the built-in gazetteer in charge, which is exactly the state
 * local development is in before the first geocoding run.
 */
export async function hydrateCoords(): Promise<number> {
  if (coordsLoaded) return Object.keys(scrapedCoords).length;
  try {
    const res = await fetch("/data/locations.json", { cache: "no-cache" });
    if (res.ok) {
      const body = (await res.json()) as {
        locations?: Record<string, { lat?: number; lon?: number }>;
      };
      const map: Record<string, Coord> = {};
      for (const [key, value] of Object.entries(body.locations ?? {})) {
        if (typeof value?.lat === "number" && typeof value?.lon === "number") {
          map[key] = { lat: value.lat, lon: value.lon };
        }
      }
      scrapedCoords = map;
    }
  } catch {
    /* fall back to the gazetteer */
  }
  coordsLoaded = true;
  return Object.keys(scrapedCoords).length;
}

/**
 * Coordinates for a location, preferring the scraped (real) value.
 *
 * `resolveCoord` is what callers should use for sorting and display; `geocode`
 * remains the pure gazetteer lookup so the fallback stays testable on its own.
 */
export function resolveCoord(location?: string): Coord | null {
  if (!location) return null;
  const key = location.trim();
  const real = scrapedCoords[key];
  if (real) return real;
  return geocode(location);
}

const EARTH_RADIUS_KM = 6371;

/** Great-circle distance in km between two coordinates. */
export function haversineKm(a: Coord, b: Coord): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** Round a distance for display: "12 km", "340 km", "1,240 km". */
export function formatDistance(km: number): string {
  if (km < 1) return "<1 km";
  if (km < 10) return `${km.toFixed(1)} km`;
  return `${Math.round(km).toLocaleString()} km`;
}
