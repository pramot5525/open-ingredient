"""
classify_foods_local.py
Classify foods as 'ingredient' or 'dish' using a local model via Ollama.

Requirements:
    pip install openai          # Ollama uses OpenAI-compatible API
    ollama pull qwen2.5:7b      # or gemma3:4b, llama3.2:8b

Usage:
    python classify_foods_local.py
    python classify_foods_local.py --model qwen2.5:14b --workers 4
"""

import csv
import json
import re
import argparse
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from tqdm import tqdm

INPUT_CSV  = Path(__file__).parent / "data" / "nutrients.csv"
OUTPUT_CSV = Path(__file__).parent / "data" / "classifications.csv"

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


def load_foods(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def classify_one(client: OpenAI, model: str, food: dict) -> tuple[str, dict]:
    """Classify a single food row. Returns (food_id, result_dict)."""
    content = (
        f"Thai name: {food['food_name_th']}\n"
        f"English name: {food['food_name_en']}\n"
        f"Food group: {food['food_group']}\n"
        f"Subgroup: {food['food_subgroup']}\n"
        f"Type: {food['food_type']}"
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
        # Extract JSON even if model adds extra text around it
        match = re.search(r'\{.*?\}', text, re.DOTALL)
        result = json.loads(match.group()) if match else {}
        if result.get("classification") not in ("ingredient", "dish"):
            result["classification"] = "unknown"
        result.setdefault("reason", "")
        return food["food_id"], result
    except Exception as e:
        return food["food_id"], {"classification": "unknown", "reason": str(e)}


def write_output(foods: list[dict], results: dict[str, dict], path: Path) -> None:
    fields = [
        "food_id", "food_name_th", "food_name_en",
        "food_group", "food_type", "classification", "reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for food in foods:
            r = results.get(food["food_id"], {"classification": "unknown", "reason": "missing"})
            writer.writerow({
                "food_id":        food["food_id"],
                "food_name_th":   food["food_name_th"],
                "food_name_en":   food["food_name_en"],
                "food_group":     food["food_group"],
                "food_type":      food["food_type"],
                "classification": r["classification"],
                "reason":         r["reason"],
            })


def main(model: str, workers: int, input_path: Path, output_path: Path) -> None:
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",  # Ollama doesn't need a real key
    )

    foods = load_foods(input_path)
    print(f"Loaded {len(foods)} foods  |  model: {model}  |  workers: {workers}")

    results: dict[str, dict] = {}
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(classify_one, client, model, food): food for food in foods}
        with tqdm(total=len(foods), desc="Classifying", unit="food") as bar:
            for future in as_completed(futures):
                food_id, result = future.result()
                with lock:
                    results[food_id] = result
                bar.update(1)

    write_output(foods, results, output_path)

    counts: dict[str, int] = {}
    for r in results.values():
        c = r.get("classification", "unknown")
        counts[c] = counts.get(c, 0) + 1

    print(f"\nSaved → {output_path}")
    for label, n in sorted(counts.items()):
        print(f"  {label:12}: {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify foods using local Ollama model")
    parser.add_argument("--model",   "-m", default="qwen2.5:7b",    help="Ollama model name")
    parser.add_argument("--workers", "-w", default=4, type=int,     help="Parallel requests")
    parser.add_argument("--input",   "-i", default=str(INPUT_CSV))
    parser.add_argument("--output",  "-o", default=str(OUTPUT_CSV))
    args = parser.parse_args()
    main(args.model, args.workers, Path(args.input), Path(args.output))
