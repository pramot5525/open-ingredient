-- Migration: deduplicate nutrients table
-- Strategy: keep lowest id per name_en group as canonical, remap all references, delete duplicates.

BEGIN;

-- 1. Build mapping: duplicate id → canonical id (lowest id per name_en)
CREATE TEMP TABLE nutrient_id_map AS
SELECT
    dup.id  AS old_id,
    keep.id AS new_id
FROM nutrients dup
JOIN (
    SELECT lower(trim(name_en)) AS key, min(id) AS id
    FROM nutrients
    WHERE name_en IS NOT NULL AND name_en <> ''
    GROUP BY lower(trim(name_en))
) keep ON lower(trim(dup.name_en)) = keep.key
WHERE dup.id <> keep.id;

-- 2. Delete food_nutrients rows that would conflict after remapping
--    (canonical row already exists → discard the duplicate)
DELETE FROM food_nutrients fn
USING nutrient_id_map m
WHERE fn.nutrient_id = m.old_id
  AND EXISTS (
      SELECT 1 FROM food_nutrients fn2
      WHERE fn2.food_id = fn.food_id AND fn2.nutrient_id = m.new_id
  );

-- 3. Remap remaining food_nutrients to canonical nutrient_id
UPDATE food_nutrients fn
SET nutrient_id = m.new_id
FROM nutrient_id_map m
WHERE fn.nutrient_id = m.old_id;

-- 4. Remap nutrients.parent_id to canonical
UPDATE nutrients n
SET parent_id = m.new_id
FROM nutrient_id_map m
WHERE n.parent_id = m.old_id;

-- 5. Delete duplicate nutrient rows
DELETE FROM nutrients
WHERE id IN (SELECT old_id FROM nutrient_id_map);

DROP TABLE nutrient_id_map;

-- 6. Verify
SELECT lower(trim(name_en)) AS key, count(*) AS cnt, array_agg(id) AS ids
FROM nutrients
WHERE name_en IS NOT NULL AND name_en <> ''
GROUP BY lower(trim(name_en))
HAVING count(*) > 1;

COMMIT;
