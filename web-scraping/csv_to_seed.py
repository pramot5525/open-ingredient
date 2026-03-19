"""
csv_to_seed.py
Transform nutrients.csv → PostgreSQL seed SQL matching schema.sql.

Usage:
    python csv_to_seed.py                          # uses defaults
    python csv_to_seed.py --input data/nutrients.csv --output data/seed.sql

"tr" (trace) values are imported as NULL.
All nutrient amounts are per 100 g edible portion.
"""

import csv
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean(value: str) -> str | None:
    """Return None for empty/trace/N/A values."""
    v = value.strip()
    if v in ("", "tr", "N/A", "n/a", "-"):
        return None
    return v


def numeric(value: str) -> str:
    """Return SQL literal: NULL or a number."""
    v = clean(value)
    if v is None:
        return "NULL"
    try:
        float(v)
        return v
    except ValueError:
        return "NULL"


def text(value: str) -> str:
    """Return SQL literal: NULL or single-quoted escaped string."""
    v = clean(value)
    if v is None:
        return "NULL"
    return "'" + v.replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Static lookup data
# ---------------------------------------------------------------------------

# (id, name_th, name_en)
UNITS = [
    (1, "กิโลแคลอรี่", "kilocalorie"),   # kcal
    (2, "กรัม",        "gram"),           # g
    (3, "มิลลิกรัม",   "milligram"),      # mg
    (4, "ไมโครกรัม",   "microgram"),      # µg
]

UNIT_KCAL, UNIT_G, UNIT_MG, UNIT_UG = 1, 2, 3, 4

# (id, csv_col, name_en, name_th, type, unit_id, parent_id)
NUTRIENTS: list[tuple] = [
    # --- proximate ---
    ( 1, "energy",         "Energy",                  "พลังงาน",                      "proximate", UNIT_KCAL, None),
    ( 2, "water",          "Water",                   "น้ำ",                           "proximate", UNIT_G,    None),
    ( 3, "protein",        "Protein",                 "โปรตีน",                        "proximate", UNIT_G,    None),
    ( 4, "fat",            "Fat",                     "ไขมัน",                         "proximate", UNIT_G,    None),
    ( 5, "carbohydrate",   "Carbohydrate",            "คาร์โบไฮเดรต",                  "proximate", UNIT_G,    None),
    ( 6, "fibre",          "Fibre",                   "ใยอาหาร",                       "proximate", UNIT_G,    None),
    ( 7, "ash",            "Ash",                     "เถ้า",                          "proximate", UNIT_G,    None),
    ( 8, "sugar",          "Sugar",                   "น้ำตาล",                        "proximate", UNIT_G,    None),
    ( 9, "energy_fat",     "Energy from fat",         "พลังงานจากไขมัน",               "proximate", UNIT_KCAL, None),
    (10, "fat_all",        "Total fat",               "ไขมันทั้งหมด",                  "proximate", UNIT_G,    None),
    (11, "fat_saturated",  "Saturated fat",           "ไขมันอิ่มตัว",                  "proximate", UNIT_G,    None),
    # --- minerals ---
    (12, "calcium",        "Calcium",                 "แคลเซียม",                      "mineral",   UNIT_MG,   None),
    (13, "phosphorus",     "Phosphorus",              "ฟอสฟอรัส",                      "mineral",   UNIT_MG,   None),
    (14, "magnesium",      "Magnesium",               "แมกนีเซียม",                    "mineral",   UNIT_MG,   None),
    (15, "sodium",         "Sodium",                  "โซเดียม",                       "mineral",   UNIT_MG,   None),
    (16, "potassium",      "Potassium",               "โพแทสเซียม",                    "mineral",   UNIT_MG,   None),
    (17, "iron",           "Iron",                    "เหล็ก",                         "mineral",   UNIT_MG,   None),
    (18, "copper",         "Copper",                  "ทองแดง",                        "mineral",   UNIT_MG,   None),
    (19, "zinc",           "Zinc",                    "สังกะสี",                       "mineral",   UNIT_MG,   None),
    (20, "iodine",         "Iodine",                  "ไอโอดีน",                       "mineral",   UNIT_MG,   None),
    (21, "selenium",       "Selenium",                "ซีลีเนียม",                     "mineral",   UNIT_UG,   None),
    # --- vitamins ---
    (22, "betacarotene",   "Beta-carotene",           "เบต้าแคโรทีน",                  "vitamin",   UNIT_UG,   None),
    (23, "retinol",        "Retinol",                 "เรตินอล",                       "vitamin",   UNIT_UG,   None),
    (24, "vitamin_A",      "Vitamin A",               "วิตามินเอ",                     "vitamin",   UNIT_UG,   None),
    (25, "thiamin",        "Thiamin",                 "ไทอามิน",                       "vitamin",   UNIT_MG,   None),
    (26, "riboflavin",     "Riboflavin",              "ไรโบฟลาวิน",                    "vitamin",   UNIT_MG,   None),
    (27, "niacin",         "Niacin",                  "ไนอาซิน",                       "vitamin",   UNIT_MG,   None),
    (28, "vitamin_C",      "Vitamin C",               "วิตามินซี",                     "vitamin",   UNIT_MG,   None),
    (29, "vitamin_E",      "Vitamin E",               "วิตามินอี",                     "vitamin",   UNIT_MG,   None),
    (30, "folate",         "Folate",                  "โฟเลต",                         "vitamin",   UNIT_UG,   None),
    (31, "cobalamin",      "Cobalamin (B12)",         "โคบาลามิน",                     "vitamin",   UNIT_UG,   None),
    # --- lipids ---
    (32, "cholesterol",    "Cholesterol",             "คอเลสเตอรอล",                   "lipid",     UNIT_MG,   None),
    # fatty acids — SFA
    (33, "sfa",            "SFA (total)",             "กรดไขมันอิ่มตัว (รวม)",         "fatty_acid", UNIT_G,   None),
    (34, "sfa_4_0",        "SFA 4:0 (Butyric)",      "บิวทีริก",                      "fatty_acid", UNIT_G,   33),
    (35, "sfa_6_0",        "SFA 6:0 (Caproic)",      "คาโปรอิก",                      "fatty_acid", UNIT_G,   33),
    (36, "sfa_8_0",        "SFA 8:0 (Caprylic)",     "คาไพรลิก",                      "fatty_acid", UNIT_G,   33),
    (37, "sfa_10_0",       "SFA 10:0 (Capric)",      "คาปริก",                        "fatty_acid", UNIT_G,   33),
    (38, "sfa_12_0",       "SFA 12:0 (Lauric)",      "ลอริก",                         "fatty_acid", UNIT_G,   33),
    (39, "sfa_14_0",       "SFA 14:0 (Myristic)",    "เมอร์ริสติก",                   "fatty_acid", UNIT_G,   33),
    (40, "sfa_16_0",       "SFA 16:0 (Palmitic)",    "ปาล์มิติก",                     "fatty_acid", UNIT_G,   33),
    (41, "sfa_18_0",       "SFA 18:0 (Stearic)",     "สเตียริก",                      "fatty_acid", UNIT_G,   33),
    # fatty acids — MUFA
    (42, "mufa",           "MUFA (total)",            "กรดไขมันไม่อิ่มตัวเชิงเดี่ยว (รวม)", "fatty_acid", UNIT_G, None),
    (43, "mufa_16_1",      "MUFA 16:1 (Palmitoleic)","พาลมิโทลีอิก",                  "fatty_acid", UNIT_G,   42),
    (44, "mufa_18_1",      "MUFA 18:1 (Oleic)",      "โอลีอิก",                       "fatty_acid", UNIT_G,   42),
    (45, "mufa_20_1",      "MUFA 20:1 (Gondoic)",    "กอนโดอิก",                      "fatty_acid", UNIT_G,   42),
    (46, "mufa_22_1",      "MUFA 22:1 (Erucic)",     "อีรูซิก",                       "fatty_acid", UNIT_G,   42),
    # fatty acids — PUFA
    (47, "pufa",           "PUFA (total)",            "กรดไขมันไม่อิ่มตัวเชิงซ้อน (รวม)", "fatty_acid", UNIT_G, None),
    (48, "pufa_18_2",      "PUFA 18:2 (Linoleic)",   "ลิโนลีอิก",                     "fatty_acid", UNIT_G,   47),
    (49, "pufa_18_3",      "PUFA 18:3 (α-Linolenic)","อัลฟ่า-ลิโนเลนิก",             "fatty_acid", UNIT_G,   47),
    (50, "pufa_18_4",      "PUFA 18:4",              "พูฟา 18:4",                     "fatty_acid", UNIT_G,   47),
    (51, "pufa_20_4",      "PUFA 20:4 (Arachidonic)","อาราคิโดนิก",                   "fatty_acid", UNIT_G,   47),
    (52, "pufa_20_5",      "PUFA 20:5 (EPA)",        "EPA",                           "fatty_acid", UNIT_G,   47),
    (53, "pufa_22_5",      "PUFA 22:5 (DPA)",        "DPA",                           "fatty_acid", UNIT_G,   47),
    (54, "pufa_22_6",      "PUFA 22:6 (DHA)",        "DHA",                           "fatty_acid", UNIT_G,   47),
    # --- amino acids ---
    (55, "asparticacid",   "Aspartic acid",           "กรดแอสพาร์ติก",                 "amino_acid", UNIT_MG,  None),
    (56, "threonine",      "Threonine",               "ทรีโอนีน",                      "amino_acid", UNIT_MG,  None),
    (57, "serine",         "Serine",                  "เซรีน",                         "amino_acid", UNIT_MG,  None),
    (58, "glutamic_acid",  "Glutamic acid",           "กรดกลูตามิก",                   "amino_acid", UNIT_MG,  None),
    (59, "proline",        "Proline",                 "โพรลีน",                        "amino_acid", UNIT_MG,  None),
    (60, "glycine",        "Glycine",                 "ไกลซีน",                        "amino_acid", UNIT_MG,  None),
    (61, "alanine",        "Alanine",                 "อะลานีน",                       "amino_acid", UNIT_MG,  None),
    (62, "cystine",        "Cystine",                 "ซีสทีน",                        "amino_acid", UNIT_MG,  None),
    (63, "valine",         "Valine",                  "วาลีน",                         "amino_acid", UNIT_MG,  None),
    (64, "methionine",     "Methionine",              "เมทไธโอนีน",                    "amino_acid", UNIT_MG,  None),
    (65, "isoleucine",     "Isoleucine",              "ไอโซลิวซีน",                    "amino_acid", UNIT_MG,  None),
    (66, "leucine",        "Leucine",                 "ลิวซีน",                        "amino_acid", UNIT_MG,  None),
    (67, "tryrosine",      "Tyrosine",                "ไทโรซีน",                       "amino_acid", UNIT_MG,  None),
    (68, "phenylalanine",  "Phenylalanine",           "ฟีนิลอะลานีน",                  "amino_acid", UNIT_MG,  None),
    (69, "histidine",      "Histidine",               "ฮีสทิดีน",                      "amino_acid", UNIT_MG,  None),
    (70, "lysine",         "Lysine",                  "ไลซีน",                         "amino_acid", UNIT_MG,  None),
    (71, "arginine",       "Arginine",                "อาร์จีนีน",                     "amino_acid", UNIT_MG,  None),
    (72, "total_amino_acid","Total amino acids",      "กรดอะมิโนรวม",                  "amino_acid", UNIT_MG,  None),
    # --- polyphenols ---
    (73, "catechin",       "Catechin",                "คาเทชิน",                       "polyphenol", UNIT_MG,  None),
    (74, "epicatechin",    "Epicatechin",             "อีพิคาเทชิน",                   "polyphenol", UNIT_MG,  None),
    (75, "gallic",         "Gallic acid",             "กรดแกลลิก",                     "polyphenol", UNIT_MG,  None),
]

# Quick lookup: csv_col → (nutrient_id, unit_id)
NUTRIENT_BY_COL: dict[str, tuple[int, int]] = {
    col: (nid, uid) for nid, col, _, _, _, uid, _ in NUTRIENTS
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(input_path: Path, output_path: Path) -> None:
    rows: list[dict] = []
    with input_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    # -----------------------------------------------------------------------
    # Build category hierarchy from food_group / food_subgroup
    # groups:    name_th → category id   (parent = NULL)
    # subgroups: (name_th, group_id) → category id   (parent = group id)
    # -----------------------------------------------------------------------
    groups:    dict[str, int]             = {}
    subgroups: dict[tuple[str, int], int] = {}

    # Pass 1: collect all groups first so IDs are stable before assigning subgroup IDs
    for row in rows:
        g = clean(row["food_group"]) or "ไม่ระบุ"
        if g not in groups:
            groups[g] = len(groups) + 1

    # Pass 2: assign subgroup IDs starting after all group IDs
    for row in rows:
        g = clean(row["food_group"]) or "ไม่ระบุ"
        s = clean(row["food_subgroup"])
        if s and s != "ไม่ระบุ":
            key = (s, groups[g])
            if key not in subgroups:
                subgroups[key] = len(groups) + len(subgroups) + 1

    # category_id for each food row (most specific available)
    def category_id_for(row: dict) -> int:
        g     = clean(row["food_group"]) or "ไม่ระบุ"
        g_id  = groups[g]
        s     = clean(row["food_subgroup"])
        if s and s != "ไม่ระบุ":
            return subgroups[(s, g_id)]
        return g_id

    # -----------------------------------------------------------------------
    # Write SQL
    # -----------------------------------------------------------------------
    lines: list[str] = []
    a = lines.append

    a("-- =============================================================")
    a("-- Auto-generated seed data from nutrients.csv")
    a("-- Generated by web-scraping/csv_to_seed.py")
    a("-- =============================================================")
    a("")
    a("BEGIN;")
    a("")

    # --- units --------------------------------------------------------------
    a("-- units")
    a("INSERT INTO units (id, name_th, name_en) VALUES")
    a(",\n".join(f"  ({uid}, {text(nth)}, {text(nen)})" for uid, nth, nen in UNITS) + ";")
    a("")

    # --- categories ---------------------------------------------------------
    a("-- categories (food_group = root, food_subgroup = child)")
    a("INSERT INTO categories (id, name_th, name_en, parent_id) VALUES")
    cat_vals: list[str] = []
    for gname, gid in sorted(groups.items(), key=lambda x: x[1]):
        cat_vals.append(f"  ({gid}, {text(gname)}, NULL, NULL)")
    for (sname, gid), sid in sorted(subgroups.items(), key=lambda x: x[1]):
        cat_vals.append(f"  ({sid}, {text(sname)}, NULL, {gid})")
    a(",\n".join(cat_vals) + ";")
    a("")

    # --- nutrients ----------------------------------------------------------
    a("-- nutrients")
    a("INSERT INTO nutrients (id, name_th, name_en, type, parent_id) VALUES")
    n_vals: list[str] = []
    for nid, _col, nen, nth, ntype, _uid, parent in NUTRIENTS:
        pid = str(parent) if parent is not None else "NULL"
        n_vals.append(f"  ({nid}, {text(nth)}, {text(nen)}, '{ntype}', {pid})")
    a(",\n".join(n_vals) + ";")
    a("")

    # --- foods --------------------------------------------------------------
    a("-- foods (weight=100 g, energy per 100 g edible portion)")
    a("INSERT INTO foods (id, name_th, name_en, category_id, weight, weight_unit, energy, energy_unit, source, source_id) VALUES")
    food_vals: list[str] = []
    for food_id, row in enumerate(rows, start=1):
        cat_id    = category_id_for(row)
        name_th   = text(row["food_name_th"])
        name_en   = text(row["food_name_en"])
        energy    = numeric(row["energy"])
        source_id = text(row["food_id"])
        food_vals.append(
            f"  ({food_id}, {name_th}, {name_en}, {cat_id}, 100, {UNIT_G}, {energy}, {UNIT_KCAL}, 'thaifcd', {source_id})"
        )
    a(",\n".join(food_vals) + ";")
    a("")

    # --- food_nutrients (EAV) -----------------------------------------------
    a("-- food_nutrients (one row per food × nutrient, NULL amounts skipped)")
    a("INSERT INTO food_nutrients (food_id, nutrient_id, amount, unit) VALUES")
    fn_vals: list[str] = []
    for food_id, row in enumerate(rows, start=1):
        for csv_col, (nid, uid) in NUTRIENT_BY_COL.items():
            val = numeric(row[csv_col])
            if val == "NULL":
                continue
            fn_vals.append(f"  ({food_id}, {nid}, {val}, {uid})")
    a(",\n".join(fn_vals) + ";")
    a("")

    # --- reset sequences ----------------------------------------------------
    a("-- Reset sequences so SERIAL picks up after seeded ids")
    a("SELECT setval('units_id_seq',      (SELECT MAX(id) FROM units));")
    a("SELECT setval('categories_id_seq', (SELECT MAX(id) FROM categories));")
    a("SELECT setval('nutrients_id_seq',  (SELECT MAX(id) FROM nutrients));")
    a("SELECT setval('foods_id_seq',      (SELECT MAX(id) FROM foods));")
    a("")
    a("COMMIT;")
    a("")

    output_path.write_text("\n".join(lines), encoding="utf-8")

    total_fn = sum(
        1
        for row in rows
        for csv_col in NUTRIENT_BY_COL
        if numeric(row[csv_col]) != "NULL"
    )
    print(f"OK  Wrote {len(rows)} food rows -> {output_path}")
    print(f"    categories:    {len(groups) + len(subgroups)} ({len(groups)} groups, {len(subgroups)} subgroups)")
    print(f"    nutrients:     {len(NUTRIENTS)}")
    print(f"    food_nutrients:{total_fn}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transform nutrients.csv → PostgreSQL seed SQL")
    parser.add_argument(
        "--input", "-i",
        default=str(Path(__file__).parent / "data" / "nutrients.csv"),
        help="Path to nutrients.csv (default: data/nutrients.csv)",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(Path(__file__).parent / "data" / "seed.sql"),
        help="Output SQL file path (default: data/seed.sql)",
    )
    args = parser.parse_args()
    main(Path(args.input), Path(args.output))
