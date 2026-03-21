-- Seed: food_units — เครื่องปรุง/วัตถุดิบ พร้อม grams_per_unit ต่อหน่วยครัวไทย
-- เพิ่ม serving units ใหม่เข้า units table ก่อน แล้ว insert food_units

-- ══════════════════════════════════════════════════════
-- 1. เพิ่มหน่วยวัดสำหรับเครื่องปรุงที่ยังไม่มี
-- ══════════════════════════════════════════════════════
INSERT INTO units (name_th, name_en) VALUES
    ('ช้อนชา',   'teaspoon'),
    ('ช้อนโต๊ะ',  'tablespoon'),
    ('ถ้วยตวง',  'measuring cup'),
    ('กลีบ',     'clove'),
    ('แว่น',     'slice'),
    ('ก้อน',     'block'),
    ('หยด',      'drop'),
    ('ช้อนกาแฟ', 'coffee spoon'),
    ('กำ',       'handful'),
    ('ใบ',       'leaf'),
    ('ต้น',      'stalk'),
    ('หัว',      'head'),
    ('ผล',      'fruit/pod')
ON CONFLICT DO NOTHING;

-- ══════════════════════════════════════════════════════
-- 2. ดึง unit_id มาใช้ผ่าน subquery
-- ══════════════════════════════════════════════════════
INSERT INTO food_units (food_id, unit_id, grams_per_unit, notes)
SELECT food_id, unit_id, grams_per_unit, notes FROM (VALUES

    -- ════ น้ำปลา id=956 ════
    (956, (SELECT id FROM units WHERE name_en='teaspoon'),    5.00,  'น้ำปลาแท้ 1 ช้อนชา ~5 ml'),
    (956, (SELECT id FROM units WHERE name_en='tablespoon'),  15.00, 'น้ำปลาแท้ 1 ช้อนโต๊ะ ~15 ml'),

    -- ════ น้ำตาลทรายแดง id=953 ════
    (953, (SELECT id FROM units WHERE name_en='teaspoon'),    4.00,  NULL),
    (953, (SELECT id FROM units WHERE name_en='tablespoon'),  12.00, NULL),
    (953, (SELECT id FROM units WHERE name_en='measuring cup'), 200.00, 'ถ้วยตวง 240 ml น้ำตาล ~200 g'),

    -- ════ น้ำตาลโตนด id=950 ════
    (950, (SELECT id FROM units WHERE name_en='teaspoon'),    4.00,  NULL),
    (950, (SELECT id FROM units WHERE name_en='tablespoon'),  12.00, NULL),
    (950, (SELECT id FROM units WHERE name_en='block'),       15.00, 'น้ำตาลโตนดก้อนกลมขนาดปกติ'),

    -- ════ น้ำตาลมะพร้าว id=952 ════
    (952, (SELECT id FROM units WHERE name_en='teaspoon'),    4.00,  NULL),
    (952, (SELECT id FROM units WHERE name_en='tablespoon'),  12.00, NULL),
    (952, (SELECT id FROM units WHERE name_en='block'),       15.00, NULL),

    -- ════ น้ำตาลกรวด id=954 ════
    (954, (SELECT id FROM units WHERE name_en='tablespoon'),  12.00, NULL),
    (954, (SELECT id FROM units WHERE name_en='block'),       10.00, 'ก้อนเล็ก'),

    -- ════ เกลือสมุทร id=969 ════
    (969, (SELECT id FROM units WHERE name_en='teaspoon'),    6.00,  '1 ช้อนชาเกลือ ~6 g'),
    (969, (SELECT id FROM units WHERE name_en='tablespoon'),  18.00, NULL),

    -- ════ กะปิ id=903 ════
    (903, (SELECT id FROM units WHERE name_en='teaspoon'),    5.00,  NULL),
    (903, (SELECT id FROM units WHERE name_en='tablespoon'),  15.00, NULL),

    -- ════ กระเทียม id=906 ════
    (906, (SELECT id FROM units WHERE name_en='clove'),       5.00,  '1 กลีบขนาดกลาง'),
    (906, (SELECT id FROM units WHERE name_en='head'),       40.00,  '1 หัวขนาดกลาง ~8 กลีบ'),
    (906, (SELECT id FROM units WHERE name_en='teaspoon'),    3.00,  'กระเทียมสับ 1 ช้อนชา'),
    (906, (SELECT id FROM units WHERE name_en='tablespoon'),  9.00,  'กระเทียมสับ 1 ช้อนโต๊ะ'),

    -- ════ กระเทียมป่น id=934 ════
    (934, (SELECT id FROM units WHERE name_en='teaspoon'),    2.80,  'ผง 1 ช้อนชา'),
    (934, (SELECT id FROM units WHERE name_en='tablespoon'),  8.40,  'ผง 1 ช้อนโต๊ะ'),

    -- ════ ขิงแก่ id=220 ════
    (220, (SELECT id FROM units WHERE name_en='slice'),       5.00,  '1 แว่น หนา ~3 mm'),
    (220, (SELECT id FROM units WHERE name_en='teaspoon'),    2.00,  'ขิงขูด 1 ช้อนชา'),
    (220, (SELECT id FROM units WHERE name_en='tablespoon'),  6.00,  'ขิงขูด 1 ช้อนโต๊ะ'),

    -- ════ แป้งข้าวเจ้า id=46 ════
    (46, (SELECT id FROM units WHERE name_en='teaspoon'),     2.60,  NULL),
    (46, (SELECT id FROM units WHERE name_en='tablespoon'),   8.00,  NULL),
    (46, (SELECT id FROM units WHERE name_en='measuring cup'), 125.00, 'แป้ง 1 ถ้วยตวง 240 ml ~125 g'),

    -- ════ เนยเค็ม id=895 ════
    (895, (SELECT id FROM units WHERE name_en='teaspoon'),    4.70,  NULL),
    (895, (SELECT id FROM units WHERE name_en='tablespoon'),  14.00, NULL),
    (895, (SELECT id FROM units WHERE name_en='measuring cup'), 225.00, 'เนย 1 ถ้วยตวง ~225 g (2 sticks)')

) AS t(food_id, unit_id, grams_per_unit, notes)
ON CONFLICT (food_id, unit_id) DO UPDATE
    SET grams_per_unit = EXCLUDED.grams_per_unit,
        notes          = EXCLUDED.notes;
