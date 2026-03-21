// seed-embeddings generates embeddings for all foods and upserts them
// into the food_embeddings table using a local Ollama model by default.
//
// Usage (local Ollama):
//
//	cd api
//	go run ./cmd/seed-embeddings
//
// Usage (OpenAI):
//
//	EMBEDDING_BASE_URL=https://api.openai.com \
//	EMBEDDING_MODEL=text-embedding-3-small \
//	EMBEDDING_API_KEY=sk-... \
//	go run ./cmd/seed-embeddings
//
// The command is idempotent: already-embedded foods are updated via ON CONFLICT.
package main

import (
	"context"
	"log"
	"open-ingredient/api/internal/adapter/repository"
	"open-ingredient/api/internal/domain/embedding"
	"open-ingredient/api/internal/infrastructure/config"
	"open-ingredient/api/internal/infrastructure/db"
	infraEmbedding "open-ingredient/api/internal/infrastructure/embedding"

	"github.com/joho/godotenv"
)

type foodRow struct {
	ID     uint
	NameTh string
	NameEn string
}

func main() {
	_ = godotenv.Load(".env")

	cfg := config.Load()
	log.Printf("embedder: model=%s  base=%s", cfg.EmbeddingModel, cfg.EmbeddingBaseURL)

	gormDB, err := db.NewPostgres(cfg)
	if err != nil {
		log.Fatalf("db connect: %v", err)
	}

	embedder := infraEmbedding.NewHTTPEmbedder(cfg.EmbeddingBaseURL, cfg.EmbeddingModel, cfg.EmbeddingAPIKey)
	embeddingRepo := repository.NewEmbeddingRepository(gormDB)
	svc := embedding.NewService(embeddingRepo, embedder)

	ctx := context.Background()

	var foods []foodRow
	if err := gormDB.WithContext(ctx).
		Raw("SELECT id, name_th, name_en FROM foods ORDER BY id").
		Scan(&foods).Error; err != nil {
		log.Fatalf("fetch foods: %v", err)
	}
	log.Printf("found %d foods to embed", len(foods))

	alreadyEmbedded, err := svc.EmbeddedCount(ctx)
	if err != nil {
		log.Fatalf("count embeddings: %v", err)
	}
	log.Printf("already embedded: %d", alreadyEmbedded)

	ok, failed := 0, 0
	for i, f := range foods {
		ft := embedding.FoodText{FoodID: f.ID, NameTh: f.NameTh, NameEn: f.NameEn}
		if err := svc.EmbedFood(ctx, ft); err != nil {
			log.Printf("[%d/%d] FAIL food_id=%d: %v", i+1, len(foods), f.ID, err)
			failed++
		} else {
			log.Printf("[%d/%d] OK   food_id=%d  %q", i+1, len(foods), f.ID, embedding.BuildText(ft))
			ok++
		}
	}

	log.Printf("done: %d embedded, %d failed", ok, failed)
}
