package repository

import (
	"context"
	"fmt"
	"open-ingredient/api/internal/domain/embedding"
	"strings"

	pgvector "github.com/pgvector/pgvector-go"
	"gorm.io/gorm"
)

// EmbeddingRepository is the driven adapter for food_embeddings using raw SQL + pgvector.
type EmbeddingRepository struct {
	db *gorm.DB
}

func NewEmbeddingRepository(db *gorm.DB) *EmbeddingRepository {
	return &EmbeddingRepository{db: db}
}

// vectorLiteral formats a []float32 as a PostgreSQL vector literal '[x,x,x,...]'.
func vectorLiteral(v []float32) string {
	parts := make([]string, len(v))
	for i, f := range v {
		parts[i] = fmt.Sprintf("%g", f)
	}
	return "[" + strings.Join(parts, ",") + "]"
}

// Upsert inserts or updates the embedding for (food_id, model).
func (r *EmbeddingRepository) Upsert(ctx context.Context, e embedding.FoodEmbedding) error {
	return r.db.WithContext(ctx).Exec(`
		INSERT INTO food_embeddings (food_id, text, embedding, model)
		VALUES (?, ?, ?, ?)
		ON CONFLICT (food_id, model)
		DO UPDATE SET text = EXCLUDED.text, embedding = EXCLUDED.embedding
	`, e.FoodID, e.Text, pgvector.NewVector(e.Vector), e.Model).Error
}

// SearchSimilar returns the top-limit foods ordered by cosine distance to vector.
func (r *EmbeddingRepository) SearchSimilar(ctx context.Context, vector []float32, limit int) ([]embedding.SimilarFood, error) {
	type row struct {
		FoodID     uint    `gorm:"column:food_id"`
		NameTh     string  `gorm:"column:name_th"`
		NameEn     string  `gorm:"column:name_en"`
		Similarity float64 `gorm:"column:similarity"`
	}

	lit := vectorLiteral(vector)
	sql := fmt.Sprintf(`
		SELECT fe.food_id,
		       f.name_th,
		       f.name_en,
		       (1 - (fe.embedding <=> '%s'::vector))::float8 AS similarity
		FROM food_embeddings fe
		JOIN foods f ON f.id = fe.food_id
		ORDER BY fe.embedding <=> '%s'::vector
		LIMIT ?
	`, lit, lit)

	var rows []row
	if err := r.db.WithContext(ctx).Raw(sql, limit).Scan(&rows).Error; err != nil {
		return nil, err
	}

	results := make([]embedding.SimilarFood, len(rows))
	for i, rw := range rows {
		results[i] = embedding.SimilarFood{
			FoodID:     rw.FoodID,
			NameTh:     rw.NameTh,
			NameEn:     rw.NameEn,
			Similarity: rw.Similarity,
		}
	}
	return results, nil
}

// CountByModel returns how many embeddings exist for a given model name.
func (r *EmbeddingRepository) CountByModel(ctx context.Context, model string) (int64, error) {
	var count int64
	err := r.db.WithContext(ctx).
		Raw("SELECT COUNT(*) FROM food_embeddings WHERE model = ?", model).
		Scan(&count).Error
	return count, err
}
