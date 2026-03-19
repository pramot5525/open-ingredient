"""
classify_foods.py
Use Claude API (Message Batches) to classify each food as 'ingredient' or 'dish'.

Usage:
    python classify_foods.py
    python classify_foods.py --input data/nutrients.csv --output data/classifications.csv

Output columns: food_id, food_name_th, food_name_en, food_group, food_type, classification, reason
"""

import csv
import json
import time
import argparse
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

INPUT_CSV  = Path(__file__).parent / "data" / "nutrients.csv"
OUTPUT_CSV = Path(__file__).parent / "data" / "classifications.csv"

SYSTEM_PROMPT = """\
You are a Thai food expert classifying items from the Thai Food Composition Database (THAIFCD).

Classify each item as exactly ONE of:
- "ingredient" : A raw, whole, or minimally processed food used as an ingredient.
  Examples: raw vegetables, fruits, grains, raw meat, eggs, milk, dried beans,
            spices, seasoning sauces, herbs, insects, roots.
- "dish"       : A cooked or prepared dish that combines multiple ingredients.
  Examples: curries, stir-fries, soups, noodle dishes, fried rice, salads (yam),
            Thai desserts (kanom), baked goods with multiple components.

Respond ONLY with a JSON object — no extra text:
{"classification": "ingredient" | "dish", "reason": "<one sentence in English>"}
"""


def load_foods(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_requests(foods: list[dict]) -> list[Request]:
    requests = []
    for food in foods:
        content = (
            f"Thai name: {food['food_name_th']}\n"
            f"English name: {food['food_name_en']}\n"
            f"Food group: {food['food_group']}\n"
            f"Subgroup: {food['food_subgroup']}\n"
            f"Type: {food['food_type']}"
        )
        requests.append(
            Request(
                custom_id=food["food_id"],
                params=MessageCreateParamsNonStreaming(
                    model="claude-haiku-4-5",
                    max_tokens=150,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content}],
                    output_config={
                        "format": {
                            "type": "json_schema",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "classification": {
                                        "type": "string",
                                        "enum": ["ingredient", "dish"],
                                    },
                                    "reason": {"type": "string"},
                                },
                                "required": ["classification", "reason"],
                                "additionalProperties": False,
                            },
                        }
                    },
                ),
            )
        )
    return requests


def poll_batch(client: anthropic.Anthropic, batch_id: str) -> None:
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            print(
                f"  Done — succeeded: {batch.request_counts.succeeded}, "
                f"errored: {batch.request_counts.errored}"
            )
            return
        print(
            f"  {batch.processing_status} | "
            f"processing: {batch.request_counts.processing} | "
            f"succeeded: {batch.request_counts.succeeded}"
        )
        time.sleep(15)


def collect_results(
    client: anthropic.Anthropic, batch_id: str
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            text = next(
                (b.text for b in result.result.message.content if b.type == "text"),
                "{}",
            )
            try:
                results[result.custom_id] = json.loads(text)
            except json.JSONDecodeError:
                results[result.custom_id] = {
                    "classification": "unknown",
                    "reason": "JSON parse error",
                }
        else:
            results[result.custom_id] = {
                "classification": "unknown",
                "reason": f"batch error: {result.result.type}",
            }
    return results


def write_output(
    foods: list[dict], results: dict[str, dict], output_path: Path
) -> None:
    fields = [
        "food_id", "food_name_th", "food_name_en",
        "food_group", "food_type", "classification", "reason",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
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


def summarise(results: dict[str, dict]) -> None:
    counts: dict[str, int] = {}
    for r in results.values():
        c = r.get("classification", "unknown")
        counts[c] = counts.get(c, 0) + 1
    for label, n in sorted(counts.items()):
        print(f"  {label:12}: {n}")


def main(input_path: Path, output_path: Path) -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    foods = load_foods(input_path)
    print(f"Loaded {len(foods)} foods from {input_path}")

    requests = build_requests(foods)
    print(f"Creating batch ({len(requests)} requests, model: claude-haiku-4-5)...")

    batch = client.messages.batches.create(requests=requests)
    print(f"Batch ID: {batch.id}")

    poll_batch(client, batch.id)

    results = collect_results(client, batch.id)
    write_output(foods, results, output_path)

    print(f"\nSaved → {output_path}")
    summarise(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Classify foods as ingredient/dish using Claude API Batches"
    )
    parser.add_argument("--input",  "-i", default=str(INPUT_CSV))
    parser.add_argument("--output", "-o", default=str(OUTPUT_CSV))
    args = parser.parse_args()
    main(Path(args.input), Path(args.output))
