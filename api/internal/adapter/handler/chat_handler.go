package handler

import (
	"open-ingredient/api/internal/domain/chat"

	"github.com/gofiber/fiber/v2"
)

// ChatHandler handles RAG-based nutrition chat requests.
type ChatHandler struct {
	svc *chat.Service
}

func NewChatHandler(svc *chat.Service) *ChatHandler {
	return &ChatHandler{svc: svc}
}

// RegisterRoutes mounts chat endpoints on the given router group.
func (h *ChatHandler) RegisterRoutes(r fiber.Router) {
	r.Post("/foods/chat/kcal", h.chatKcal)
}

// ChatKcalRequest is the request body for POST /foods/chat/kcal.
type ChatKcalRequest struct {
	Message string `json:"message" example:"ข้าวมันไก่ 1 จาน ให้กี่แคล"`
}

// ChatKcalSource is one matched food source used to generate the reply.
type ChatKcalSource struct {
	FoodID     uint    `json:"food_id"`
	NameTh     string  `json:"name_th"`
	NameEn     string  `json:"name_en"`
	Similarity float64 `json:"similarity"`
}

// ChatKcalResponse is the response for POST /foods/chat/kcal.
type ChatKcalResponse struct {
	Reply   string           `json:"reply"`
	Sources []ChatKcalSource `json:"sources"`
}

// chatKcal godoc
// @Summary      RAG nutrition chat
// @Description  Answers free-text questions about calories and nutrients using vector search + local LLM (Ollama).
// @Tags         foods
// @Accept       json
// @Produce      json
// @Param        body  body      ChatKcalRequest   true  "User question in Thai or English"
// @Success      200   {object}  ChatKcalResponse
// @Failure      400   {object}  ErrorResponse
// @Failure      500   {object}  ErrorResponse
// @Router       /foods/chat/kcal [post]
func (h *ChatHandler) chatKcal(c *fiber.Ctx) error {
	var req ChatKcalRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "invalid request body"})
	}
	if req.Message == "" {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "message is required"})
	}

	result, err := h.svc.Chat(c.Context(), req.Message)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Error: err.Error()})
	}

	sources := make([]ChatKcalSource, len(result.Sources))
	for i, s := range result.Sources {
		sources[i] = ChatKcalSource{
			FoodID:     s.FoodID,
			NameTh:     s.NameTh,
			NameEn:     s.NameEn,
			Similarity: s.Similarity,
		}
	}

	return c.JSON(ChatKcalResponse{
		Reply:   result.Reply,
		Sources: sources,
	})
}
