-- Seed: flavors
INSERT INTO flavors (id, name_th, name_en) VALUES
  (1,  'หวาน',       'Sweet'),
  (2,  'เค็ม',        'Salty'),
  (3,  'เปรี้ยว',      'Sour'),
  (4,  'ขม',         'Bitter'),
  (5,  'เผ็ด',        'Spicy'),
  (6,  'มัน',         'Savory / Umami'),
  (7,  'ฝาด',        'Astringent'),
  (8,  'เฝื่อน',       'Pungent'),
  (9,  'หอม',        'Aromatic'),
  (10, 'จืด',        'Bland')
ON CONFLICT (id) DO NOTHING;

SELECT setval('flavors_id_seq', (SELECT MAX(id) FROM flavors));
