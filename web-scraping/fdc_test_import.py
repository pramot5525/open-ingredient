"""
Quick test: fetch 10 Foundation foods from FDC API and insert into DB.
Populates: units, nutrients, foods, food_nutrients
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
import requests
import psycopg2
from psycopg2.extras import execute_values

load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY  = os.environ["FDC_API_KEY"]
BASE_URL = "https://api.nal.usda.gov/fdc/v1"

DB = dict(
    dbname   = os.getenv("POSTGRES_DB",      "open_ingredient"),
    user     = os.getenv("POSTGRES_USER",    "postgres"),
    password = os.getenv("POSTGRES_PASSWORD","postgres"),
    host     = os.getenv("POSTGRES_HOST",    "localhost"),
    port     = os.getenv("POSTGRES_PORT",    "5432"),
)

# ---------------------------------------------------------------------------

def api_get(path, **params):
    r = requests.get(f"{BASE_URL}/{path}", params={"api_key": API_KEY, **params}, timeout=30)
    r.raise_for_status()
    return r.json()


def upsert_unit(cur, name_en: str) -> int:
    cur.execute(
        "INSERT INTO units (name_en) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
        (name_en,)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT id FROM units WHERE name_en = %s", (name_en,))
    return cur.fetchone()[0]


def upsert_nutrient(cur, name_en: str, unit_name: str) -> int:
    cur.execute(
        "INSERT INTO nutrients (name_en) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
        (name_en,)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT id FROM nutrients WHERE name_en = %s", (name_en,))
    return cur.fetchone()[0]


def import_food(cur, food: dict):
    fdc_id      = str(food["fdcId"])
    description = food.get("description", "")

    # Find energy value (kcal)
    energy_val  = None
    energy_unit_id = None
    for fn in food.get("foodNutrients", []):
        nutrient = fn.get("nutrient", {})
        if "Energy" in nutrient.get("name", "") and nutrient.get("unitName") == "kcal":
            energy_val = fn.get("amount")
            energy_unit_id = upsert_unit(cur, "kcal")
            break

    # Upsert food (skip if source_id already exists)
    cur.execute("SELECT id FROM foods WHERE source = 'fdc' AND source_id = %s", (fdc_id,))
    row = cur.fetchone()
    if row:
        print(f"  skip (already exists): {description}")
        return

    cur.execute(
        """INSERT INTO foods (name_en, energy, energy_unit, source, source_id)
           VALUES (%s, %s, %s, 'fdc', %s) RETURNING id""",
        (description, energy_val, energy_unit_id, fdc_id)
    )
    food_id = cur.fetchone()[0]

    # Insert food_nutrients
    rows = []
    for fn in food.get("foodNutrients", []):
        nutrient = fn.get("nutrient", {})
        name     = nutrient.get("name", "").strip()
        unit_name= nutrient.get("unitName", "")
        amount   = fn.get("amount")
        if not name or amount is None:
            continue
        nutrient_id = upsert_nutrient(cur, name, unit_name)
        unit_id     = upsert_unit(cur, unit_name) if unit_name else None
        rows.append((food_id, nutrient_id, amount, unit_id))

    if rows:
        execute_values(
            cur,
            "INSERT INTO food_nutrients (food_id, nutrient_id, amount, unit) VALUES %s",
            rows
        )

    print(f"  inserted: [{fdc_id}] {description} — {len(rows)} nutrients")


def main():
    # 1. Fetch 10 Foundation food IDs
    print("Fetching 10 Foundation food IDs from FDC ...")
    items = api_get("foods/list", dataType="Foundation", pageSize=10, pageNumber=1)
    fdc_ids = [item["fdcId"] for item in items]
    print(f"Got IDs: {fdc_ids}\n")

    # 2. Fetch full detail for each
    conn = psycopg2.connect(**DB)
    try:
        with conn:
            cur = conn.cursor()
            for fdc_id in fdc_ids:
                print(f"Fetching fdcId={fdc_id} ...")
                food = api_get(f"food/{fdc_id}", format="full")
                import_food(cur, food)
                time.sleep(0.3)
    finally:
        conn.close()

    print("\nDone. Check your DB:")
    print("  SELECT id, name_en, energy, source_id FROM foods;")
    print("  SELECT count(*) FROM food_nutrients;")


if __name__ == "__main__":
    main()
