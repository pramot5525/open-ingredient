"""
Thai Food Composition Database (THAIFCD) scraper.
Step 1 – fetch all food IDs from the list page (DataTables, all rows in HTML):
  https://thaifcd.anamai.moph.go.th/nss/search.php
Step 2 – scrape each food's nutrient page:
  Foundation: https://thaifcd.anamai.moph.go.th/nss/view.php?fID=<ID>
  Branded:    https://thaifcd.anamai.moph.go.th/nss/view_branded.php?fID=<ID>

Branded foods have IDs starting with "R" (e.g. R010001).

Output: data/nutrients.csv  (appended incrementally)
        data/ids.txt        (all IDs discovered from list page, cached)
        data/failed.txt     (IDs that returned no data or errored)
"""

import csv
import re
import time
import random
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LIST_URL     = "https://thaifcd.anamai.moph.go.th/nss/search.php"
BASE_URL     = "https://thaifcd.anamai.moph.go.th/nss/view.php"
BRANDED_URL  = "https://thaifcd.anamai.moph.go.th/nss/view_branded.php"

DELAY_MIN = 0.5
DELAY_MAX = 1.5

OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_CSV = OUTPUT_DIR / "nutrients.csv"
FAILED_TXT = OUTPUT_DIR / "failed.txt"
IDS_TXT    = OUTPUT_DIR / "ids.txt"

SESSION_TIMEOUT = 20

# Foundation food nutrient element IDs
NUTRIENT_IDS = [
    # Main
    "energy", "water", "protein", "fat", "carbohydrate", "fibre", "ash",
    # Minerals
    "calcium", "phosphorus", "magnesium", "sodium", "potassium",
    "iron", "copper", "zinc", "iodine", "selenium",
    # Vitamins & others
    "betacarotene", "retinol", "vitamin_A", "thiamin", "riboflavin",
    "niacin", "vitamin_C", "vitamin_E", "folate", "cobalamin",
    # Other components
    "sugar", "cholesterol",
    # Saturated fatty acids
    "sfa", "sfa_4_0", "sfa_6_0", "sfa_8_0", "sfa_10_0",
    "sfa_12_0", "sfa_14_0", "sfa_16_0", "sfa_18_0",
    # Monounsaturated fatty acids
    "mufa", "mufa_16_1", "mufa_18_1", "mufa_20_1", "mufa_22_1",
    # Polyunsaturated fatty acids
    "pufa", "pufa_18_2", "pufa_18_3", "pufa_18_4",
    "pufa_20_4", "pufa_20_5", "pufa_22_5", "pufa_22_6",
    # Amino acids
    "asparticacid", "threonine", "serine", "glutamic_acid", "proline",
    "glycine", "alanine", "cystine", "valine", "methionine",
    "isoleucine", "leucine", "tryrosine", "phenylalanine",
    "histidine", "lysine", "arginine", "total_amino_acid",
    # Polyphenols
    "catechin", "epicatechin", "gallic",
]

# Branded food nutrient element IDs (food-label style subset)
BRANDED_NUTRIENT_IDS = [
    "energy", "energy_fat", "fat_all", "fat_saturated",
    "cholesterol", "protein", "carbohydrate", "fibre", "sugar", "sodium",
    "vitamin_A", "thiamin", "riboflavin", "calcium", "iron",
]

CSV_FIELDS = (
    ["food_id", "food_type", "food_name_th", "food_name_en", "food_group", "food_subgroup"]
    + NUTRIENT_IDS
    + [nid for nid in BRANDED_NUTRIENT_IDS if nid not in NUTRIENT_IDS]
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def text(el) -> str:
    return el.get_text(strip=True) if el else ""


def fetch_all_ids(session: requests.Session) -> list[str]:
    """
    Fetch the full food list from search.php.
    The page uses DataTables (client-side pagination) so all rows are in one HTML response.
    Captures both foundation (numeric) and branded (R-prefix) food IDs.
    Caches results to data/ids.txt.
    """
    if IDS_TXT.exists():
        ids = [line.strip() for line in IDS_TXT.read_text(encoding="utf-8").splitlines() if line.strip()]
        log.info(f"Loaded {len(ids)} IDs from cache ({IDS_TXT})")
        return ids

    log.info(f"Fetching food list from {LIST_URL} ...")
    resp = session.get(LIST_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    ids = []
    # Match both view.php?fID= and view_branded.php?fID=
    for a in soup.find_all("a", href=re.compile(r"fID=")):
        m = re.search(r"fID=(\w+)", a["href"])
        if m:
            ids.append(m.group(1))

    # Deduplicate while preserving order
    seen: set[str] = set()
    ids = [fid for fid in ids if not (fid in seen or seen.add(fid))]  # type: ignore[func-returns-value]

    log.info(f"Found {len(ids)} unique food IDs "
             f"({sum(1 for i in ids if i.startswith('R'))} branded, "
             f"{sum(1 for i in ids if not i.startswith('R'))} foundation)")
    IDS_TXT.write_text("\n".join(ids), encoding="utf-8")
    return ids


def load_done_ids(csv_path: Path) -> set[str]:
    if not csv_path.exists():
        return set()
    done: set[str] = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add(row["food_id"])
    return done


def load_failed_ids(failed_path: Path) -> set[str]:
    if not failed_path.exists():
        return set()
    with open(failed_path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def parse_foundation_page(html: str, food_id: str) -> dict | None:
    """Parse a foundation food page (view.php)."""
    soup = BeautifulSoup(html, "lxml")

    # Validity check: view-id element must exist and h3 must have a real name
    if soup.find(id="view-id") is None:
        return None
    h3 = soup.find("h3")
    if h3 is None or not re.sub(r'[\s\(\)\-,.]', '', text(h3)):
        return None

    # Food name: "Thai name (English name)"
    raw = text(h3)
    en_match = re.search(r'\(([A-Za-z][^)]+)\)', raw)
    name_en = en_match.group(1).strip() if en_match else ""
    name_th = re.sub(r'\s*\([A-Za-z][^)]*\)\s*$', '', raw).strip()

    # Food group / subgroup from td cells
    food_group = ""
    food_subgroup = ""
    for td in soup.find_all("td"):
        cell = text(td)
        if "กลุ่มอาหาร" in cell and "กลุ่มอาหารย่อย" not in cell and not food_group:
            m = re.search(r':\s*(.+?)(?:\s*\(|$)', cell, re.DOTALL)
            if m:
                food_group = m.group(1).strip()
        if "กลุ่มอาหารย่อย" in cell and not food_subgroup:
            m = re.search(r':\s*(.+)', cell)
            if m:
                food_subgroup = m.group(1).strip()

    row: dict = {
        "food_id": food_id,
        "food_type": "foundation",
        "food_name_th": name_th,
        "food_name_en": name_en,
        "food_group": food_group,
        "food_subgroup": food_subgroup,
    }
    for nid in NUTRIENT_IDS:
        el = soup.find(id=nid)
        row[nid] = text(el) if el else ""

    if all(row[nid] == "" for nid in NUTRIENT_IDS):
        return None
    return row


def parse_branded_page(html: str, food_id: str) -> dict | None:
    """Parse a branded food page (view_branded.php)."""
    soup = BeautifulSoup(html, "lxml")

    # Branded pages have no view-id; use energy element as validity check
    if soup.find(id="energy") is None:
        return None
    h3 = soup.find("h3")
    if h3 is None or not re.sub(r'[\s\(\)\-,.]', '', text(h3)):
        return None

    raw = text(h3)
    en_match = re.search(r'\(([A-Za-z][^)]+)\)', raw)
    name_en = en_match.group(1).strip() if en_match else ""
    name_th = re.sub(r'\s*\([A-Za-z][^)]*\)\s*$', '', raw).strip()

    food_group = ""
    food_subgroup = ""
    for td in soup.find_all("td"):
        cell = text(td)
        if "กลุ่มอาหาร" in cell and "กลุ่มอาหารย่อย" not in cell and not food_group:
            m = re.search(r':\s*(.+?)(?:\s*\(|$)', cell, re.DOTALL)
            if m:
                food_group = m.group(1).strip()
        if "กลุ่มอาหารย่อย" in cell and not food_subgroup:
            m = re.search(r':\s*(.+)', cell)
            if m:
                food_subgroup = m.group(1).strip()

    row: dict = {
        "food_id": food_id,
        "food_type": "branded",
        "food_name_th": name_th,
        "food_name_en": name_en,
        "food_group": food_group,
        "food_subgroup": food_subgroup,
    }
    for nid in BRANDED_NUTRIENT_IDS:
        el = soup.find(id=nid)
        row[nid] = text(el) if el else ""

    if all(row.get(nid, "") == "" for nid in BRANDED_NUTRIENT_IDS):
        return None
    return row


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

WORKERS = 8  # concurrent threads — tune up/down based on server tolerance

def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        "Referer": "https://thaifcd.anamai.moph.go.th/nss/",
    })
    return s

# Thread-local session so each thread keeps its own TCP connection pool
_local = threading.local()

def _session() -> requests.Session:
    if not hasattr(_local, "session"):
        _local.session = _make_session()
    return _local.session


def _scrape_one(food_id: str) -> tuple[str, dict | None]:
    """Fetch and parse one food page. Returns (food_id, data_or_None)."""
    is_branded = food_id.startswith("R")
    url   = BRANDED_URL if is_branded else BASE_URL
    parse = parse_branded_page if is_branded else parse_foundation_page
    try:
        resp = _session().get(url, params={"fID": food_id}, timeout=SESSION_TIMEOUT)
        resp.raise_for_status()
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        return food_id, parse(resp.text, food_id)
    except requests.RequestException as e:
        log.warning(f"{food_id}: request error – {e}")
        time.sleep(DELAY_MAX)
        return food_id, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log.addHandler(logging.FileHandler(OUTPUT_DIR / "scraper.log", encoding="utf-8"))

    # Need one session just for the ID list fetch
    seed_session = _make_session()

    done_ids   = load_done_ids(OUTPUT_CSV)
    failed_ids = load_failed_ids(FAILED_TXT)
    skip_ids   = done_ids | failed_ids
    log.info(f"Already done: {len(done_ids)}, already failed: {len(failed_ids)}")

    all_ids = fetch_all_ids(seed_session)
    todo    = [fid for fid in all_ids if fid not in skip_ids]
    log.info(f"IDs to scrape: {len(todo)} of {len(all_ids)} — using {WORKERS} workers")

    csv_exists = OUTPUT_CSV.exists()
    csv_file   = open(OUTPUT_CSV, "a", newline="", encoding="utf-8")
    writer     = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
    if not csv_exists:
        writer.writeheader()

    failed_file = open(FAILED_TXT, "a", encoding="utf-8")
    write_lock  = threading.Lock()

    success = 0
    failed  = 0

    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(_scrape_one, fid): fid for fid in todo}
            with tqdm(total=len(todo), desc="Scraping", unit="food") as bar:
                for future in as_completed(futures):
                    food_id, data = future.result()
                    with write_lock:
                        if data is None:
                            log.debug(f"{food_id}: no data")
                            failed_file.write(food_id + "\n")
                            failed_file.flush()
                            failed += 1
                        else:
                            writer.writerow(data)
                            csv_file.flush()
                            success += 1
                            log.debug(f"{food_id}: OK – {data.get('food_name_th', '')}")
                    bar.update(1)

    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    finally:
        csv_file.close()
        failed_file.close()
        log.info(f"Done. Success: {success}, failed/skipped: {failed}")
        log.info(f"Output: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
