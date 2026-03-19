# Open Ingredient

Food composition database with a REST API for searching ingredients and calculating kilocalories, built on Thai FCD and USDA FoodData Central data.

---

## Quick Start

```bash
# 1. Copy env and fill in values
cp .env.example .env

# 2. Start Postgres + API (with hot reload)
docker-compose up --build

# 3. Load seed data (first time only)
psql -h localhost -U postgres -d open_ingredient < web-scraping/data/seed.sql
psql -h localhost -U postgres -d open_ingredient < seeds/flavors.sql
psql -h localhost -U postgres -d open_ingredient < seeds/processes.sql
```

---

## API

**Base URL:** `http://localhost:3000/api/v1`

### Swagger UI

> **http://localhost:3000/api/docs/index.html**

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/foods/search` | Search foods by name (Thai or English) |
| `GET` | `/foods/:id` | Get food detail with all nutrients |
| `POST` | `/foods/kcal` | Calculate kcal from ingredients with weights |
| `GET` | `/health` | Health check |

### Examples

**Search**
```
GET /api/v1/foods/search?q=ข้าว&page=1&limit=20
```

**Food detail**
```
GET /api/v1/foods/17
```

**Calculate kcal**
```bash
curl -X POST http://localhost:3000/api/v1/foods/kcal \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": [
      { "food_id": 17,   "weight_g": 120 },
      { "food_id": 1302, "weight_g": 100 }
    ]
  }'
```

Response includes `total_kcal`, per-item breakdown, and nutrients merged across all ingredients (amounts scaled to requested weight, rounded to 2 decimal places).

---

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Go 1.25 |
| HTTP | Fiber v2 |
| ORM | GORM + PostgreSQL |
| Docs | Swagger 2.0 (swaggo) |
| Hot reload | Air |
| Container | Docker Compose |

### Architecture

Hexagonal (Ports & Adapters) inside `api/`:

```
domain/food/        ← business logic, no framework deps
adapter/handler/    ← Fiber HTTP handlers (driving)
adapter/repository/ ← GORM PostgreSQL (driven)
infrastructure/     ← config, DB connection
```

---

## Data Sources

| Source | Description |
|--------|-------------|
| `THAIFCD` | Thai Food Composition Database (scraped) |
| `FDC_FOUNDATION` | USDA FoodData Central — Foundation Foods |
| `FDC_SR_LEGACY` | USDA FoodData Central — SR Legacy |

### Re-scrape / re-seed

```bash
cd web-scraping

# Scrape Thai FCD
python scraper.py

# Generate seed SQL from CSV
python csv_to_seed.py

# Classify ingredient vs dish using Claude API
python classify_foods.py
```
