package embedding

import (
	"context"
	"fmt"
	"strings"
)

// Embedder generates a vector embedding from a text string.
type Embedder interface {
	Embed(ctx context.Context, text string) ([]float32, error)
	Model() string
}

// FoodText is a minimal food record used for bulk embedding.
type FoodText struct {
	FoodID uint
	NameTh string
	NameEn string
}

// BuildText returns the text to embed for a food record.
// Format: "NameTh NameEn" (omits empty parts).
func BuildText(f FoodText) string {
	parts := make([]string, 0, 2)
	if f.NameTh != "" {
		parts = append(parts, f.NameTh)
	}
	if f.NameEn != "" {
		parts = append(parts, f.NameEn)
	}
	return strings.Join(parts, " ")
}

// Service contains the embedding use-cases.
type Service struct {
	repo     Repository
	embedder Embedder
}

func NewService(repo Repository, embedder Embedder) *Service {
	return &Service{repo: repo, embedder: embedder}
}

// SemanticSearch embeds the query text and returns the most similar foods.
func (s *Service) SemanticSearch(ctx context.Context, query string, limit int) ([]SimilarFood, error) {
	if limit <= 0 || limit > 100 {
		limit = 10
	}
	vec, err := s.embedder.Embed(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("embedding query: %w", err)
	}
	return s.repo.SearchSimilar(ctx, vec, limit)
}

// EmbedFood generates an embedding for a single food and upserts it.
func (s *Service) EmbedFood(ctx context.Context, f FoodText) error {
	text := BuildText(f)
	if text == "" {
		return fmt.Errorf("food %d has no name", f.FoodID)
	}
	vec, err := s.embedder.Embed(ctx, text)
	if err != nil {
		return fmt.Errorf("embed food %d: %w", f.FoodID, err)
	}
	return s.repo.Upsert(ctx, FoodEmbedding{
		FoodID: f.FoodID,
		Text:   text,
		Vector: vec,
		Model:  s.embedder.Model(),
	})
}

// EmbeddedCount returns how many foods have been embedded with the current model.
func (s *Service) EmbeddedCount(ctx context.Context) (int64, error) {
	return s.repo.CountByModel(ctx, s.embedder.Model())
}
