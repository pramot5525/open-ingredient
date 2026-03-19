# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**open-ingredient** is a food composition database with:
1. A **Python data pipeline** (web scraping + AI classification → PostgreSQL)
2. A planned **Go REST API** (Go Fiber + GORM, hexagonal architecture) for searching ingredients and calculating kcal

## Database

### Run PostgreSQL
```bash
docker-compose up -d
```

### Connect
```bash
psql -h localhost -U postgres -d open_ingredient
```

### Schema
- `schema.sql` — PostgreSQL DDL (source of truth)
- `schema.dbml` — DBML diagram source

### Key Tables
- `foods` — ingredient/dish records with `source` tracking (THAIFCD, FDC_FOUNDATION, FDC_SR_LEGACY)
- `food_nutrients` — EAV table linking foods to nutrient values (per 100g)
- `nutrients` — nutrient definitions (hierarchical; includes Energy in kcal)
- `units` — measurement units (kcal, g, mg, µg)
- `categories` — hierarchical food categories (parent_id self-reference)

### Load seed data
```bash
psql -h localhost -U postgres -d open_ingredient < web-scraping/data/seed.sql
psql -h localhost -U postgres -d open_ingredient < seeds/flavors.sql
psql -h localhost -U postgres -d open_ingredient < seeds/processes.sql
```

## Python Data Pipeline

### Setup
```bash
cd web-scraping
pip install -r requirements.txt
```

### Scripts (run from `web-scraping/`)
| Script | Purpose |
|--------|---------|
| `scraper.py` | Scrape Thai FCD → `data/nutrients.csv` |
| `csv_to_seed.py` | Transform CSV → `data/seed.sql` |
| `classify_foods.py` | Classify foods via Claude Batches API |
| `classify_foods_db.py` | Classify from DB using local Ollama model |
| `fdc_fetcher.py` | Fetch USDA FoodData Central via API |
| `fcd.usda/seed.py` | Load USDA JSON files into PostgreSQL |

### Environment
Copy `.env.example` → `.env` and fill in `FDC_API_KEY` (USDA FoodData Central).

## Planned Go API (Hexagonal Architecture)

The Go service should be scaffolded in a `api/` subdirectory with this structure:

```
api/
├── cmd/server/main.go          # Entry point: load config, wire dependencies, start Fiber
├── internal/
│   ├── domain/                 # Pure business logic, no framework dependencies
│   │   ├── food/
│   │   │   ├── entity.go       # Food, Nutrient structs
│   │   │   ├── repository.go   # Repository interface (port)
│   │   │   └── service.go      # Use cases: SearchFoods, CalcKcal
│   ├── adapter/
│   │   ├── handler/            # Fiber HTTP handlers (driving adapters)
│   │   │   ├── food_handler.go
│   │   │   └── dto.go          # Request/Response JSON structs
│   │   └── repository/         # GORM implementations (driven adapters)
│   │       └── food_repo.go
│   └── infrastructure/
│       ├── db/                 # GORM + PostgreSQL connection
│       └── config/             # env config loading
├── docs/                       # OpenAPI 3.0 spec (swag-generated or hand-written)
├── go.mod
└── go.sum
```

### Key API endpoints
- `GET /api/v1/foods/search?q=<name>&page=<n>&limit=<n>` — search foods table by name
- `POST /api/v1/foods/kcal` — calculate kcal from ingredients list with weights (g)

### CalcKcal request/response pattern
```json
// POST /api/v1/foods/kcal
// Request
{ "ingredients": [{ "food_id": 1, "weight_g": 150 }] }

// Response
{ "total_kcal": 245.5, "items": [{ "food_id": 1, "food_name": "Rice", "kcal": 245.5 }] }
```

### kcal calculation
`kcal = (food_nutrients.value / 100) * weight_g`
where `food_nutrients.nutrient_id` matches the Energy (kcal) nutrient.

### Recommended Go libraries
- `github.com/gofiber/fiber/v2` — HTTP framework
- `gorm.io/gorm` + `gorm.io/driver/postgres` — ORM
- `github.com/swaggo/swag` — OpenAPI 3.0 generation from annotations
- `github.com/joho/godotenv` — env loading

### OpenAPI
Use `swag init` from `api/` after adding Swag annotations to handlers. Serve spec at `/api/docs`.

## Architecture Notes

- The database uses **EAV (Entity-Attribute-Value)** for `food_nutrients` — join via `nutrients.name = 'Energy'` and `units.symbol = 'kcal'` to find kcal values
- Food sources: `THAIFCD` (Thai), `FDC_FOUNDATION` / `FDC_SR_LEGACY` (USDA) — the `source` column on `foods`
- Nutrient hierarchy: `nutrients.parent_id` groups macros, vitamins, minerals, amino acids
- Category hierarchy: `categories.parent_id` links subgroups to groups
- All nutrient values stored per **100g** basis
