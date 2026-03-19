-- =============================================================
-- Open Ingredient — PostgreSQL Schema
-- =============================================================

CREATE TABLE units (
    id       SERIAL       PRIMARY KEY,
    name_th  VARCHAR(255),
    name_en  VARCHAR(255)
);

-- Self-referential: ข้าว → ข้าวเจ้า → ข้าวหอมมะลิ
CREATE TABLE categories (
    id        SERIAL       PRIMARY KEY,
    name_th   VARCHAR(255),
    name_en   VARCHAR(255),
    parent_id INT          REFERENCES categories(id)  -- null = root
);

CREATE TABLE processes (
    id       SERIAL       PRIMARY KEY,
    name_th  VARCHAR(255),  -- ต้ม, ผัด, นึ่ง
    name_en  VARCHAR(255)
);

CREATE TABLE flavors (
    id       SERIAL       PRIMARY KEY,
    name_th  VARCHAR(255),  -- หวาน, เค็ม, เผ็ด
    name_en  VARCHAR(255)
);

-- Self-referential: e.g. SFA → fatty_acid
CREATE TABLE nutrients (
    id        SERIAL       PRIMARY KEY,
    name_th   VARCHAR(255),
    name_en   VARCHAR(255),
    type      VARCHAR,
    parent_id INT          REFERENCES nutrients(id)  -- null = root
);

CREATE TABLE recipes (
    id           SERIAL       PRIMARY KEY,
    name_th      VARCHAR(255),
    name_en      VARCHAR(255),
    category_id  INT          REFERENCES categories(id),
    energy       FLOAT,
    energy_unit  INT          REFERENCES units(id),
    source       VARCHAR,     -- e.g. thaifcd
    source_id    VARCHAR      -- original id from source
);

CREATE TABLE recipe_processes (
    id          SERIAL  PRIMARY KEY,
    recipe_id   INT     NOT NULL REFERENCES recipes(id),
    process_id  INT     NOT NULL REFERENCES processes(id)
);

CREATE TABLE recipe_flavors (
    id        SERIAL  PRIMARY KEY,
    recipe_id INT     NOT NULL REFERENCES recipes(id),
    flavor_id INT     NOT NULL REFERENCES flavors(id),
    level     INT
);

CREATE TABLE foods (
    id           SERIAL       PRIMARY KEY,
    name_th      VARCHAR(255),
    name_en      VARCHAR(255),
    category_id  INT          REFERENCES categories(id),
    weight       FLOAT,
    weight_unit  INT          REFERENCES units(id),
    energy       FLOAT,
    energy_unit  INT          REFERENCES units(id),
    source       VARCHAR,
    source_id    VARCHAR
);

CREATE TABLE food_nutrients (
    id          SERIAL   PRIMARY KEY,
    food_id     INT      NOT NULL REFERENCES foods(id),
    nutrient_id INT      NOT NULL REFERENCES nutrients(id),
    amount      FLOAT,
    unit        INT      REFERENCES units(id),
    operator    VARCHAR  -- <, ~, >
);

CREATE TABLE recipe_nutrients (
    id          SERIAL   PRIMARY KEY,
    recipe_id   INT      NOT NULL REFERENCES recipes(id),
    nutrient_id INT      NOT NULL REFERENCES nutrients(id),
    amount      FLOAT,
    unit        INT      REFERENCES units(id),
    operator    VARCHAR  -- <, ~, >
);
