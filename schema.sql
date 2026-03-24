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

CREATE TABLE brands (
    id          SERIAL       PRIMARY KEY,
    name_th     VARCHAR(255),
    name_en     VARCHAR(255),
    logo_url    VARCHAR,
    website_url VARCHAR
);

CREATE TABLE foods (
    id           SERIAL        PRIMARY KEY,
    name_th      VARCHAR(255),
    name_en      VARCHAR(255),
    category_id  INT           REFERENCES categories(id),
    brand_id     INT           REFERENCES brands(id),  -- null = generic / unbranded
    weight       FLOAT,        -- serving size (optional สำหรับ raw food)
    weight_unit  INT           REFERENCES units(id),
    energy       FLOAT,
    energy_unit  INT           REFERENCES units(id),
    is_recipe    BOOLEAN       DEFAULT false,  -- flag ว่าเป็นสูตรอาหาร
    source       VARCHAR,
    source_id    VARCHAR
);

-- Self-referential ingredients (recipes composed of foods)
CREATE TABLE food_ingredients (
    food_id        INT    NOT NULL REFERENCES foods(id),  -- recipe
    ingredient_id  INT    NOT NULL REFERENCES foods(id),  -- component
    amount         FLOAT,
    unit_id        INT    REFERENCES units(id),
    PRIMARY KEY (food_id, ingredient_id)
);

CREATE TABLE food_processes (
    food_id    INT  NOT NULL REFERENCES foods(id),
    process_id INT  NOT NULL REFERENCES processes(id),
    PRIMARY KEY (food_id, process_id)
);

CREATE TABLE food_flavors (
    food_id   INT  NOT NULL REFERENCES foods(id),
    flavor_id INT  NOT NULL REFERENCES flavors(id),
    level     INT,
    PRIMARY KEY (food_id, flavor_id)
);

CREATE TABLE food_nutrients (
    food_id     INT     NOT NULL REFERENCES foods(id),
    nutrient_id INT     NOT NULL REFERENCES nutrients(id),
    amount      FLOAT,
    unit_id     INT     REFERENCES units(id),
    operator    VARCHAR CHECK (operator IN ('<', '~', '>')),
    PRIMARY KEY (food_id, nutrient_id)
);

CREATE TABLE users (
    id         SERIAL       PRIMARY KEY,
    email      VARCHAR(255) NOT NULL UNIQUE,
    name       VARCHAR(255),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE user_meals (
    id         SERIAL      PRIMARY KEY,
    user_id    INT         NOT NULL REFERENCES users(id),
    eaten_at   TIMESTAMPTZ NOT NULL,
    meal_type  VARCHAR     NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    is_buffet  BOOLEAN     NOT NULL DEFAULT false,
    note       VARCHAR
);

CREATE INDEX ON user_meals (user_id, eaten_at);

CREATE TABLE user_meal_foods (
    id        SERIAL  PRIMARY KEY,
    meal_id   INT     NOT NULL REFERENCES user_meals(id),
    food_id   INT     NOT NULL REFERENCES foods(id),
    weight_g  FLOAT,           -- grams per serving; null if unknown (e.g. soup)
    volume_ml FLOAT,           -- ml for liquids
    qty       INT     NOT NULL DEFAULT 1,  -- number of servings/plates
    note      VARCHAR,
    UNIQUE (meal_id, food_id)
);
