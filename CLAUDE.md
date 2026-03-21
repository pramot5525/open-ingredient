# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**open-ingredient** is a food composition database with:
1. A **Python data pipeline** (web scraping + AI classification → PostgreSQL)
2. A **Go REST API** (`api/`) — Fiber + GORM, hexagonal architecture, running at `:3000`
3. Planned: **RAG/vector search** (pgvector), **vision food recognition**, **barcode lookup**

## Development

### Start everything (DB + API with hot-reload)
```bash
docker-compose up --build
```
API hot-reloads via Air on `.go`/`.toml`/`.env` changes. Swagger UI: `http://localhost:3000/api/docs/index.html`

### DB only
```bash
docker-compose up -d db
psql -h localhost -U postgres -d open_ingredient
```

### Go API (local, outside Docker)
```bash
cd api
go build ./...
go run ./cmd/server          # direct
air                          # with hot-reload
```

### Regenerate Swagger docs
```bash
cd api
swag init -g cmd/server/main.go
```
Run this after modifying Swag annotations in handlers. Output goes to `api/docs/`.

### Python pipeline
```bash
cd web-scraping
pip install -r requirements.txt
python scraper.py            # scrape Thai FCD → data/nutrients.csv
python csv_to_seed.py        # CSV → data/seed.sql
python classify_foods.py     # classify via Claude Batches API
```

### Load seed data (first time)
```bash
psql -h localhost -U postgres -d open_ingredient < web-scraping/data/seed.sql
psql -h localhost -U postgres -d open_ingredient < seeds/flavors.sql
psql -h localhost -U postgres -d open_ingredient < seeds/processes.sql
```

### Apply migrations
```bash
psql -h localhost -U postgres -d open_ingredient < migrations/001_merge_recipes_into_foods.sql
psql -h localhost -U postgres -d open_ingredient < migrations/002_dedup_nutrients.sql
```

## Go API Architecture

Hexagonal architecture — domain layer has zero framework dependencies:

```
cmd/server/main.go              Wire deps, start Fiber
internal/
  domain/food/
    entity.go                   Food/FoodNutrient structs; KcalFor(weightG), ScaleNutrients()
    repository.go               Repository interface (port)
    service.go                  Use cases: Search, GetByID, CalcKcal (page ≥1, limit 1–100)
  adapter/
    handler/
      food_handler.go           Fiber handlers + Swag annotations
      dto.go                    JSON request/response structs
    repository/
      food_repo.go              GORM implementation; maps DB models ↔ domain entities
  infrastructure/
    config/config.go            Env loading + DSN builder
    db/postgres.go              GORM + PostgreSQL connection
    router/router.go            Fiber routing + middleware
```

### Current endpoints
- `GET  /api/v1/foods/search?q=<name>&page=<n>&limit=<n>`
- `GET  /api/v1/foods/:id`
- `POST /api/v1/foods/kcal` — `{ "ingredients": [{ "food_id": 1, "weight_g": 150 }] }`
- `GET  /health`

### kcal formula
`kcal = (food_nutrients.amount / 100) * weight_g`
Join: `nutrients.name = 'Energy'` and resolve via `units` to confirm kcal unit.

## Database Schema

`schema.sql` is the source of truth. Key tables:

| Table | Notes |
|-------|-------|
| `foods` | `source`: THAIFCD / FDC_FOUNDATION / FDC_SR_LEGACY; `is_recipe` flag; `weight` = serving size per 100g basis |
| `food_nutrients` | EAV — `(food_id, nutrient_id)` PK; `operator` is `<`/`~`/`>` |
| `nutrients` | Hierarchical via `parent_id`; root nodes = macro groups |
| `categories` | Hierarchical via `parent_id` (e.g. ข้าว → ข้าวเจ้า → ข้าวหอมมะลิ) |
| `food_ingredients` | Recipe decomposition: `food_id` (recipe) → `ingredient_id` (component) |
| `food_flavors` | Many-to-many with intensity `level` |

## Planned Features (Roadmap)

### Phase 1 — Knowledge Base & Vector Search
- Add `pgvector` extension; embed `foods.name_th` + `foods.name_en` for semantic search
- **Alias system**: store `aliases[]` per food record; embed every alias as a separate pgvector row pointing to the same `food_id` — critical for Thai name fuzzy matching (e.g. "ผัดกะเพราหมูสับ" ≡ "กะเพราหมูราดข้าว")
- Add `default_serving_g` column to `foods` for when user omits weight
- Open Food Facts: call API directly at query time for barcode lookups (EAN → nutrients); no pre-embedding needed

### Phase 2 — Vision Pipeline
Three new endpoints sharing one `NutritionService`:
- `POST /api/v1/analyze-text` — text description → RAG retrieval → nutrient result
- `POST /api/v1/analyze-image` — photo → Vision LLM → portion category → nutrients
- `POST /api/v1/barcode` — EAN → Open Food Facts API → nutrients

Vision LLM must return structured JSON only — **do not ask for gram weights directly** (high hallucination risk). Use portion categories instead:
```json
{ "foods": [{ "name_th": "ข้าวมันไก่", "confidence": 0.85, "portion": "medium_plate" }] }
```
Map `portion` → gram range in code, not in the LLM prompt.

### Phase 3 — Flutter Client
- `image_picker` + compress before upload (reject raw >4 MB images)
- `mobile_scanner` for barcode
- Response maps into existing local meal log DB

## Architecture Notes

- All nutrient values are stored **per 100g basis** — always divide by 100 before multiplying by actual weight
- EAV `food_nutrients` requires joining `nutrients` + `units` to identify the Energy (kcal) row
- `food_ingredients` enables weighted-sum nutrient calculation for composite dishes
- The `operator` field (`<`/`~`/`>`) in `food_nutrients` indicates measurement precision (trace amounts use `<`)
- Python classifiers (`classify_foods.py` / `classify_foods_db.py`) set `foods.is_recipe` to distinguish raw ingredients from composite dishes
