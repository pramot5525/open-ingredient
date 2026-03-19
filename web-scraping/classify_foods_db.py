"""
classify_foods_db.py
Query foods from PostgreSQL and classify each as 'ingredient' or 'dish'
using a local model via Ollama.

Requirements:
    pip install openai psycopg2-binary python-dotenv
    ollama pull qwen2.5:7b

Usage:
    python classify_foods_db.py
    python classify_foods_db.py --model qwen2.5:7b --workers 4 --dry-run
    python classify_foods_db.py --update   # write results back to DB
"""

import os
import re
import json
import argparse
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv(Path(__file__).parent.parent / ".env")

DB = dict(
    dbname   = os.getenv("POSTGRES_DB",       "open_ingredient"),
    user     = os.getenv("POSTGRES_USER",     "postgres"),
    password = os.getenv("POSTGRES_PASSWORD", "postgres"),
    host     = os.getenv("POSTGRES_HOST",     "localhost"),
    port     = os.getenv("POSTGRES_PORT",     "5432"),
)

SYSTEM_PROMPT = """\
You are a Thai food expert classifying items from the Thai Food Composition Database.

Classify each item as exactly ONE of:
- "ingredient" : Raw or minimally processed food used as an ingredient.
  Examples: raw vegetables, fruits, grains, raw meat, eggs, milk, dried beans,
            spices, seasoning sauces, herbs, insects, roots.
- "dish"       : A cooked or prepared dish made from multiple ingredients.
  Examples: curries, stir-fries, soups, noodle dishes, fried rice, Thai desserts.

Respond ONLY with valid JSON — no extra text:
{"classification": "ingredient" | "dish", "reason": "<one sentence>"}
"""


def load_foods(conn) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                f.id,
                f.name_th,
                f.name_en,
                c.name_en  AS category,
                c.name_th  AS category_th,
                f.source,
                f.source_id
            FROM public.foods AS f
            LEFT JOIN public.categories AS c ON c.id = f.category_id
            ORDER BY f.id
        """)
        return [dict(row) for row in cur.fetchall()]


def classify_one(client: OpenAI, model: str, food: dict) -> tuple[int, dict]:
    """Classify a single food row. Returns (food_id, result_dict)."""
    content = (
        f"Thai name: {food['name_th'] or ''}\n"
        f"English name: {food['name_en'] or ''}\n"
        f"Category (EN): {food['category'] or ''}\n"
        f"Category (TH): {food['category_th'] or ''}\n"
        f"Source: {food['source'] or ''}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": content},
            ],
            max_tokens=120,
            temperature=0,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or "{}"
        match = re.search(r'\{.*?\}', text, re.DOTALL)
        result = json.loads(match.group()) if match else {}
        if result.get("classification") not in ("ingredient", "dish"):
            result["classification"] = "unknown"
        result.setdefault("reason", "")
        return food["id"], result
    except Exception as e:
        return food["id"], {"classification": "unknown", "reason": str(e)}


def write_results_to_db(conn, results: dict[int, dict]) -> None:
    """
    Write classification results back to the database.
    Assumes a column `kind varchar` exists on the foods table.
    Run this SQL first if the column doesn't exist:
        ALTER TABLE public.foods ADD COLUMN IF NOT EXISTS kind varchar;
    """
    rows = [
        (r["classification"], r["reason"], food_id)
        for food_id, r in results.items()
    ]
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "UPDATE public.foods SET kind = %s WHERE id = %s",
            [(row[0], row[2]) for row in rows],
        )
    conn.commit()
    print(f"Updated {len(rows)} rows in public.foods.")


def main(model: str, workers: int, update: bool, dry_run: bool) -> None:
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )

    conn = psycopg2.connect(**DB)
    try:
        foods = load_foods(conn)
        print(f"Loaded {len(foods)} foods from DB  |  model: {model}  |  workers: {workers}")

        if dry_run:
            print("--- DRY RUN: showing first 3 rows ---")
            for food in foods[:3]:
                print({k: (v.encode("utf-8", "replace").decode("utf-8") if isinstance(v, str) else v)
                       for k, v in food.items()})
            return

        results: dict[int, dict] = {}
        lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(classify_one, client, model, food): food for food in foods}
            with tqdm(total=len(foods), desc="Classifying", unit="food") as bar:
                for future in as_completed(futures):
                    food_id, result = future.result()
                    with lock:
                        results[food_id] = result
                    bar.update(1)

        # Print summary
        counts: dict[str, int] = {}
        for r in results.values():
            c = r.get("classification", "unknown")
            counts[c] = counts.get(c, 0) + 1
        for label, n in sorted(counts.items()):
            print(f"  {label:12}: {n}")

        if update:
            write_results_to_db(conn, results)
        else:
            print("\nPass --update to write results back to DB.")
            print("First, add the column:")
            print("  ALTER TABLE public.foods ADD COLUMN IF NOT EXISTS kind varchar;")

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify foods in DB using Ollama")
    parser.add_argument("--model",   "-m", default="qwen2.5:7b")
    parser.add_argument("--workers", "-w", default=4, type=int)
    parser.add_argument("--update",        action="store_true",
                        help="Write classification back to foods.kind column")
    parser.add_argument("--dry-run",       action="store_true",
                        help="Just print first few rows, don't call LLM")
    args = parser.parse_args()
    main(args.model, args.workers, args.update, args.dry_run)
