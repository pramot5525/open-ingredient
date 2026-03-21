-- food_units: maps a food to named serving units (via units table) with gram equivalents.
-- First extends the units table with serving/portion units, then creates food_units.

-- Add serving units that don't exist yet
INSERT INTO units (name_th, name_en) VALUES
    ('ห่อ',      'packet'),
    ('จาน',      'plate'),
    ('ครึ่งจาน',  'half plate'),
    ('ชาม',      'bowl'),
    ('ถ้วย',     'cup'),
    ('ทัพพี',    'ladle'),
    ('ครก',      'mortar'),
    ('ชิ้น',     'piece'),
    ('ชุด',      'set'),
    ('กล่อง',    'box'),
    ('ถุง',      'bag'),
    ('ฟอง',      'egg'),
    ('ลูก',      'fruit'),
    ('หวี',      'hand'),
    ('กิโลกรัม', 'kilogram')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS food_units (
    id              SERIAL PRIMARY KEY,
    food_id         INTEGER      NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    unit_id         INTEGER      NOT NULL REFERENCES units(id),
    grams_per_unit  NUMERIC(8,2) NOT NULL,
    notes           TEXT,
    UNIQUE (food_id, unit_id)
);

CREATE INDEX IF NOT EXISTS food_units_food_id_idx ON food_units (food_id);
