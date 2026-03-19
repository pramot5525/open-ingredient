#!/usr/bin/env python3
"""Seed USDA FoodData Central JSON into PostgreSQL."""

import json
import os
import psycopg2
from psycopg2.extras import execute_values

DB = {
    "dbname": os.getenv("POSTGRES_DB", "open_ingredient"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}

FILES = [
    ("fcd.usda/data/FoodData_Central_foundation_food_json_2025-12-18.json", "FoundationFoods", "FDC_FOUNDATION"),
    ("fcd.usda/data/FoodData_Central_sr_legacy_food_json_2018-04.json",     "SRLegacyFoods",   "FDC_SR_LEGACY"),
]


def load_foods(path, root_key):
    with open(path, encoding="utf-8") as f:
        return json.load(f)[root_key]


def ensure_unit(cur, unit_cache, name_en):
    if name_en in unit_cache:
        return unit_cache[name_en]
    cur.execute(
        "INSERT INTO units (name_en) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
        (name_en,),
    )
    row = cur.fetchone()
    if row is None:
        cur.execute("SELECT id FROM units WHERE name_en = %s", (name_en,))
        row = cur.fetchone()
    unit_cache[name_en] = row[0]
    return row[0]


def ensure_nutrient(cur, nutrient_cache, fdc_nutrient):
    fdc_id = fdc_nutrient["id"]
    if fdc_id in nutrient_cache:
        return nutrient_cache[fdc_id]
    name_en = fdc_nutrient["name"]
    cur.execute(
        "INSERT INTO nutrients (name_en) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
        (name_en,),
    )
    row = cur.fetchone()
    if row is None:
        cur.execute("SELECT id FROM nutrients WHERE name_en = %s", (name_en,))
        row = cur.fetchone()
    nutrient_cache[fdc_id] = row[0]
    return row[0]


def seed(conn, foods, source_label):
    cur = conn.cursor()
    unit_cache = {}
    nutrient_cache = {}

    # Pre-load existing units and nutrients to avoid excessive round-trips
    cur.execute("SELECT name_en, id FROM units WHERE name_en IS NOT NULL")
    unit_cache.update({r[0]: r[1] for r in cur.fetchall()})

    cur.execute("SELECT name_en, id FROM nutrients WHERE name_en IS NOT NULL")
    nutrient_cache_by_name = {r[0]: r[1] for r in cur.fetchall()}

    inserted_foods = 0
    skipped_foods = 0

    for food in foods:
        fdc_id = str(food["fdcId"])
        description = food.get("description", "")

        # Check for duplicate source_id
        cur.execute(
            "SELECT id FROM foods WHERE source = %s AND source_id = %s",
            (source_label, fdc_id),
        )
        if cur.fetchone():
            skipped_foods += 1
            continue

        # Extract energy (kcal) from foodNutrients before insert
        energy_val = None
        energy_unit_id = None
        for fn in food.get("foodNutrients", []):
            nut = fn.get("nutrient", {})
            if nut.get("name") == "Energy" and nut.get("unitName") in ("kcal", "kilocalorie"):
                energy_val = fn.get("amount")
                energy_unit_id = ensure_unit(cur, unit_cache, nut["unitName"])
                break

        # Insert food row
        cur.execute(
            """
            INSERT INTO foods (name_en, source, source_id, energy, energy_unit)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (description, source_label, fdc_id, energy_val, energy_unit_id),
        )
        food_id = cur.fetchone()[0]
        inserted_foods += 1

        # Insert food_nutrients
        nutrient_rows = []
        for fn in food.get("foodNutrients", []):
            nut = fn.get("nutrient")
            if not nut:
                continue
            amount = fn.get("amount")
            if amount is None:
                continue

            unit_name = nut.get("unitName", "")
            unit_id = ensure_unit(cur, unit_cache, unit_name) if unit_name else None

            # Resolve nutrient id
            fdc_nut_id = nut["id"]
            if fdc_nut_id not in nutrient_cache:
                nut_name = nut["name"]
                if nut_name in nutrient_cache_by_name:
                    nutrient_cache[fdc_nut_id] = nutrient_cache_by_name[nut_name]
                else:
                    nutrient_id = ensure_nutrient(cur, nutrient_cache, nut)
                    nutrient_cache_by_name[nut["name"]] = nutrient_id

            nutrient_id = nutrient_cache.get(fdc_nut_id)
            if nutrient_id is None:
                continue

            nutrient_rows.append((food_id, nutrient_id, amount, unit_id))

        if nutrient_rows:
            execute_values(
                cur,
                "INSERT INTO food_nutrients (food_id, nutrient_id, amount, unit) VALUES %s",
                nutrient_rows,
            )

    conn.commit()
    cur.close()
    return inserted_foods, skipped_foods


def main():
    print(f"Connecting to {DB['host']}:{DB['port']}/{DB['dbname']} ...")
    conn = psycopg2.connect(**DB)

    for path, root_key, source_label in FILES:
        print(f"\nLoading {path} ...")
        foods = load_foods(path, root_key)
        print(f"  {len(foods)} foods found — source={source_label}")
        inserted, skipped = seed(conn, foods, source_label)
        print(f"  inserted={inserted}  skipped(duplicate source_id)={skipped}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
