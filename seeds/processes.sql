-- Seed: processes
INSERT INTO processes (id, name_th, name_en) VALUES
  (1,  'ดิบ',           'Raw'),
  (2,  'ต้ม',           'Boiled'),
  (3,  'นึ่ง',           'Steamed'),
  (4,  'ผัด',           'Stir-fried'),
  (5,  'ทอด',          'Deep-fried'),
  (6,  'ย่าง',           'Grilled'),
  (7,  'อบ',           'Baked'),
  (8,  'ตุ๋น',           'Braised / Stewed'),
  (9,  'รมควัน',        'Smoked'),
  (10, 'หมัก',          'Marinated / Fermented'),
  (11, 'แช่แข็ง',        'Frozen'),
  (12, 'อบแห้ง',        'Dried'),
  (13, 'แปรรูป',        'Processed')
ON CONFLICT (id) DO NOTHING;

SELECT setval('processes_id_seq', (SELECT MAX(id) FROM processes));
