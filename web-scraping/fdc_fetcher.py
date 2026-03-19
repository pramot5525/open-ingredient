"""
USDA FoodData Central (FDC) API fetcher.
Fetches all Foundation foods and their full nutrient details.

Docs: https://fdc.nal.usda.gov/api-guide
API:  https://api.nal.usda.gov/fdc/v1/

Reads FDC_API_KEY from .env (or environment).

Output: data/fdc_nutrients.csv  (appended incrementally)
        data/fdc_ids.txt        (all fdcIds discovered, cached)
        data/fdc_failed.txt     (fdcIds that errored)
"""

import csv
import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY   = os.environ["FDC_API_KEY"]
BASE_URL  = "https://api.nal.usda.gov/fdc/v1"

# Food types to fetch: Foundation, SR Legacy, Survey (FNDDS), Branded
FOOD_TYPES = ["Foundation", "SR Legacy"]

PAGE_SIZE  = 200   # max allowed by FDC API
DELAY      = 0.3   # seconds between requests (be polite)

OUTPUT_DIR  = Path(__file__).parent / "data"
OUTPUT_CSV  = OUTPUT_DIR / "fdc_nutrients.csv"
FAILED_TXT  = OUTPUT_DIR / "fdc_failed.txt"
IDS_TXT     = OUTPUT_DIR / "fdc_ids.txt"

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
# API helpers
# ---------------------------------------------------------------------------

def _get(session: requests.Session, path: str, **params) -> dict:
    resp = session.get(
        f"{BASE_URL}/{path}",
        params={"api_key": API_KEY, **params},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_fdc_ids(session: requests.Session) -> list[int]:
    """Page through /foods/list to collect all fdcIds for the target food types."""
    if IDS_TXT.exists():
        ids = [int(line.strip()) for line in IDS_TXT.read_text().splitlines() if line.strip()]
        log.info(f"Loaded {len(ids)} fdcIds from cache ({IDS_TXT})")
        return ids

    ids: list[int] = []
    for food_type in FOOD_TYPES:
        page = 1
        log.info(f"Fetching ID list for dataType={food_type} ...")
        while True:
            data = _get(
                session,
                "foods/list",
                dataType=food_type,
                pageSize=PAGE_SIZE,
                pageNumber=page,
                sortBy="fdcId",
                sortOrder="asc",
            )
            if not data:
                break
            ids.extend(item["fdcId"] for item in data)
            log.info(f"  {food_type} page {page}: {len(data)} items (total so far: {len(ids)})")
            if len(data) < PAGE_SIZE:
                break
            page += 1
            time.sleep(DELAY)

    IDS_TXT.write_text("\n".join(str(i) for i in ids))
    log.info(f"Saved {len(ids)} fdcIds to {IDS_TXT}")
    return ids


def load_done_ids(csv_path: Path) -> set[int]:
    if not csv_path.exists():
        return set()
    done: set[int] = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add(int(row["fdc_id"]))
    return done


def load_failed_ids(failed_path: Path) -> set[int]:
    if not failed_path.exists():
        return set()
    with open(failed_path, encoding="utf-8") as f:
        return {int(line.strip()) for line in f if line.strip()}


def fetch_food(session: requests.Session, fdc_id: int) -> dict | None:
    """Fetch a single food by fdcId and flatten to a CSV row."""
    try:
        data = _get(session, f"food/{fdc_id}", format="full")
    except requests.RequestException as e:
        log.warning(f"{fdc_id}: request error – {e}")
        return None

    row: dict = {
        "fdc_id":        data.get("fdcId"),
        "data_type":     data.get("dataType", ""),
        "description":   data.get("description", ""),
        "food_category": (data.get("foodCategory") or {}).get("description", ""),
        "publication_date": data.get("publicationDate", ""),
    }

    # Flatten nutrients: nutrient_name → value (per 100 g)
    for fn in data.get("foodNutrients", []):
        nutrient = fn.get("nutrient", {})
        name     = nutrient.get("name", "").strip()
        unit     = nutrient.get("unitName", "")
        value    = fn.get("amount", "")
        if name:
            col = f"{name} ({unit})" if unit else name
            row[col] = value

    return row


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log.addHandler(logging.FileHandler(OUTPUT_DIR / "fdc_fetcher.log", encoding="utf-8"))

    session = requests.Session()

    done_ids   = load_done_ids(OUTPUT_CSV)
    failed_ids = load_failed_ids(FAILED_TXT)
    skip_ids   = done_ids | failed_ids
    log.info(f"Already done: {len(done_ids)}, already failed: {len(failed_ids)}")

    all_ids = fetch_all_fdc_ids(session)
    todo    = [fid for fid in all_ids if fid not in skip_ids]
    log.info(f"IDs to fetch: {len(todo)} of {len(all_ids)}")

    # Collect all field names from a sample before opening CSV
    # (we discover columns dynamically from the API response)
    fieldnames_seen: list[str] = []
    fixed_fields = ["fdc_id", "data_type", "description", "food_category", "publication_date"]

    csv_exists  = OUTPUT_CSV.exists()
    if csv_exists:
        with open(OUTPUT_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames_seen = list(reader.fieldnames or [])
    else:
        fieldnames_seen = list(fixed_fields)

    csv_file    = open(OUTPUT_CSV, "a", newline="", encoding="utf-8")
    writer      = csv.DictWriter(csv_file, fieldnames=fieldnames_seen, extrasaction="ignore")
    if not csv_exists:
        writer.writeheader()

    failed_file = open(FAILED_TXT, "a", encoding="utf-8")
    success = failed = 0

    try:
        with tqdm(total=len(todo), desc="Fetching FDC", unit="food") as bar:
            for fdc_id in todo:
                row = fetch_food(session, fdc_id)
                if row is None:
                    failed_file.write(str(fdc_id) + "\n")
                    failed_file.flush()
                    failed += 1
                else:
                    # Expand fieldnames if new nutrient columns appear
                    new_cols = [k for k in row if k not in fieldnames_seen]
                    if new_cols:
                        fieldnames_seen.extend(new_cols)
                        # Re-open writer with updated fieldnames
                        csv_file.flush()
                        csv_file.close()
                        _rewrite_header(OUTPUT_CSV, fieldnames_seen)
                        csv_file = open(OUTPUT_CSV, "a", newline="", encoding="utf-8")
                        writer   = csv.DictWriter(csv_file, fieldnames=fieldnames_seen, extrasaction="ignore")

                    writer.writerow(row)
                    csv_file.flush()
                    success += 1

                bar.update(1)
                time.sleep(DELAY)

    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    finally:
        csv_file.close()
        failed_file.close()
        log.info(f"Done. Success: {success}, failed: {failed}")
        log.info(f"Output: {OUTPUT_CSV}")


def _rewrite_header(csv_path: Path, fieldnames: list[str]):
    """Rewrite the CSV with an updated header row (data rows unchanged)."""
    tmp = csv_path.with_suffix(".tmp")
    with open(csv_path, newline="", encoding="utf-8") as fin, \
         open(tmp, "w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            writer.writerow(row)
    tmp.replace(csv_path)


if __name__ == "__main__":
    main()
