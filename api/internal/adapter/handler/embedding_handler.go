package handler

import (
	"open-ingredient/api/internal/domain/embedding"

	"github.com/gofiber/fiber/v2"
)

// EmbeddingHandler handles semantic-search requests.
type EmbeddingHandler struct {
	svc *embedding.Service
}

func NewEmbeddingHandler(svc *embedding.Service) *EmbeddingHandler {
	return &EmbeddingHandler{svc: svc}
}

// RegisterRoutes mounts embedding endpoints on the given router group.
func (h *EmbeddingHandler) RegisterRoutes(r fiber.Router) {
	r.Post("/foods/semantic-search", h.semanticSearch)
}

// SemanticSearchRequest is the request body for POST /foods/semantic-search.
type SemanticSearchRequest struct {
	Query string `json:"query"`
	Limit int    `json:"limit"`
}

// SimilarFoodItem is one result in a semantic search response.
type SimilarFoodItem struct {
	FoodID     uint    `json:"food_id"`
	NameTh     string  `json:"name_th"`
	NameEn     string  `json:"name_en"`
	Similarity float64 `json:"similarity"`
}

// SemanticSearchResponse is the response for POST /foods/semantic-search.
type SemanticSearchResponse struct {
	Query   string            `json:"query"`
	Results []SimilarFoodItem `json:"results"`
}

// semanticSearch godoc
// @Summary      Semantic (vector) food search
// @Description  Embeds the query with OpenAI and returns the most similar foods using pgvector cosine distance.
// @Tags         foods
// @Accept       json
// @Produce      json
// @Param        body  body      SemanticSearchRequest   true  "Search query and optional limit (1-100, default 10)"
// @Success      200   {object}  SemanticSearchResponse
// @Failure      400   {object}  ErrorResponse
// @Failure      500   {object}  ErrorResponse
// @Router       /foods/semantic-search [post]
func (h *EmbeddingHandler) semanticSearch(c *fiber.Ctx) error {
	var req SemanticSearchRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "invalid request body"})
	}
	if req.Query == "" {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "query is required"})
	}
	if req.Limit <= 0 {
		req.Limit = 10
	}

	similar, err := h.svc.SemanticSearch(c.Context(), req.Query, req.Limit)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Error: err.Error()})
	}

	items := make([]SimilarFoodItem, len(similar))
	for i, f := range similar {
		items[i] = SimilarFoodItem{
			FoodID:     f.FoodID,
			NameTh:     f.NameTh,
			NameEn:     f.NameEn,
			Similarity: f.Similarity,
		}
	}
	return c.JSON(SemanticSearchResponse{Query: req.Query, Results: items})
}
