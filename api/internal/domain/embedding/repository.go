package embedding

import "context"

// Repository is the port (interface) for embedding persistence.
type Repository interface {
	// Upsert inserts or updates an embedding (keyed on food_id + model).
	Upsert(ctx context.Context, e FoodEmbedding) error

	// SearchSimilar returns the top-limit foods closest to the given vector.
	SearchSimilar(ctx context.Context, vector []float32, limit int) ([]SimilarFood, error)

	// CountByModel returns how many embeddings exist for a given model name.
	CountByModel(ctx context.Context, model string) (int64, error)
}
