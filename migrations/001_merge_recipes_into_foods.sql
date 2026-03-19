-- Migration: merge recipes into foods, unify junction tables
-- Run: psql -h localhost -U postgres -d open_ingredient < migrations/001_merge_recipes_into_foods.sql

BEGIN;

-- 1. Drop old recipe tables (order matters: dependents first)
DROP TABLE IF EXISTS recipe_nutrients;
DROP TABLE IF EXISTS recipe_flavors;
DROP TABLE IF EXISTS recipe_processes;
DROP TABLE IF EXISTS recipes;

-- 2. Add is_recipe flag to foods
ALTER TABLE foods ADD COLUMN IF NOT EXISTS is_recipe BOOLEAN NOT NULL DEFAULT false;

-- 3. Fix food_nutrients: rename unit → unit_id, drop surrogate PK, add composite PK + CHECK

-- 3a. Deduplicate: keep the row with the lowest id per (food_id, nutrient_id)
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

ALTER TABLE food_nutrients DROP CONSTRAINT IF EXISTS food_nutrients_pkey;
ALTER TABLE food_nutrients DROP COLUMN IF EXISTS id;
ALTER TABLE food_nutrients RENAME COLUMN unit TO unit_id;
ALTER TABLE food_nutrients ADD CONSTRAINT food_nutrients_operator_check
    CHECK (operator IN ('<', '~', '>'));
ALTER TABLE food_nutrients ADD PRIMARY KEY (food_id, nutrient_id);

-- 4. Create food_ingredients (self-referential recipe composition)
CREATE TABLE IF NOT EXISTS food_ingredients (
    food_id        INT    NOT NULL REFERENCES foods(id),
    ingredient_id  INT    NOT NULL REFERENCES foods(id),
    amount         FLOAT,
    unit_id        INT    REFERENCES units(id),
    PRIMARY KEY (food_id, ingredient_id)
);

-- 5. Create food_processes
CREATE TABLE IF NOT EXISTS food_processes (
    food_id    INT  NOT NULL REFERENCES foods(id),
    process_id INT  NOT NULL REFERENCES processes(id),
    PRIMARY KEY (food_id, process_id)
);

-- 6. Create food_flavors
CREATE TABLE IF NOT EXISTS food_flavors (
    food_id   INT  NOT NULL REFERENCES foods(id),
    flavor_id INT  NOT NULL REFERENCES flavors(id),
    level     INT,
    PRIMARY KEY (food_id, flavor_id)
);

COMMIT;
