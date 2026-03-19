-- =============================================================
-- dedup_nutrients.sql
-- Remove duplicate rows in the nutrients table.
--
-- Strategy:
--   For each group of rows with the same (lower-case) name_en,
--   keep the one with the lowest id (canonical) and remap all
--   foreign-key references before deleting the duplicates.
--
-- Safe to run multiple times (idempotent).
-- =============================================================

BEGIN;

-- -----------------------------------------------------------
-- 1. Inspect duplicates before making any changes
-- -----------------------------------------------------------
SELECT
    lower(name_en)          AS name_en_key,
    count(*)                AS total,
    array_agg(id ORDER BY id) AS ids
FROM nutrients
GROUP BY lower(name_en)
HAVING count(*) > 1
ORDER BY name_en_key;


-- -----------------------------------------------------------
-- 2. Build a mapping: duplicate id → canonical id
--    canonical = lowest id among the group
-- -----------------------------------------------------------
CREATE TEMP TABLE nutrient_id_map AS
SELECT
    dup.id   AS old_id,
    keep.id  AS new_id
FROM nutrients dup
JOIN (
    -- one row per name_en group: the canonical (lowest) id
    SELECT lower(name_en) AS name_key, min(id) AS id
    FROM nutrients
    GROUP BY lower(name_en)
) keep ON lower(dup.name_en) = keep.name_key
WHERE dup.id <> keep.id;   -- only the non-canonical rows

-- Preview the mapping
SELECT old_id, new_id,
       d.name_en AS duplicate_name,
       k.name_en AS canonical_name
FROM nutrient_id_map m
JOIN nutrients d ON d.id = m.old_id
JOIN nutrients k ON k.id = m.new_id
ORDER BY new_id;


-- -----------------------------------------------------------
-- 3. Remap food_nutrients → canonical nutrient_id
-- -----------------------------------------------------------
UPDATE food_nutrients fn
SET nutrient_id = m.new_id
FROM nutrient_id_map m
WHERE fn.nutrient_id = m.old_id;


-- -----------------------------------------------------------
-- 4. Remap recipe_nutrients → canonical nutrient_id
-- -----------------------------------------------------------
UPDATE recipe_nutrients rn
SET nutrient_id = m.new_id
FROM nutrient_id_map m
WHERE rn.nutrient_id = m.old_id;


-- -----------------------------------------------------------
-- 5. Remap nutrients.parent_id → canonical parent
-- -----------------------------------------------------------
UPDATE nutrients n
SET parent_id = m.new_id
FROM nutrient_id_map m
WHERE n.parent_id = m.old_id;


-- -----------------------------------------------------------
-- 6. Remove food_nutrients rows that are now duplicate
--    (same food_id + nutrient_id after remapping — keep min id)
-- -----------------------------------------------------------
DELETE FROM food_nutrients
WHERE id IN (
    SELECT id FROM (
        SELECT id,
               row_number() OVER (
                   PARTITION BY food_id, nutrient_id
                   ORDER BY id
               ) AS rn
        FROM food_nutrients
    ) t
    WHERE rn > 1
);


-- -----------------------------------------------------------
-- 7. Delete the duplicate nutrient rows
-- -----------------------------------------------------------
DELETE FROM nutrients
WHERE id IN (SELECT old_id FROM nutrient_id_map);


-- -----------------------------------------------------------
-- 8. Verify — should return 0 rows if clean
-- -----------------------------------------------------------
SELECT
    lower(name_en) AS name_en_key,
    count(*)       AS total,
    array_agg(id ORDER BY id) AS ids
FROM nutrients
GROUP BY lower(name_en)
HAVING count(*) > 1;


DROP TABLE nutrient_id_map;

COMMIT;
