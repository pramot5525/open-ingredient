package router

import (
	"open-ingredient/api/internal/adapter/handler"

	"github.com/gofiber/fiber/v2"
)

// Handlers bundles all driving-adapter handlers.
type Handlers struct {
	Food      *handler.FoodHandler
	Embedding *handler.EmbeddingHandler
	Chat      *handler.ChatHandler
}

// Register mounts all API versions on the app.
// To add v2: add registerV2(v2, h) below — v1 is untouched.
func Register(app *fiber.App, h Handlers) {
	api := app.Group("/api")

	v1 := api.Group("/v1", apiVersionHeader("1"))
	registerV1(v1, h)
}

func registerV1(r fiber.Router, h Handlers) {
	h.Food.RegisterRoutes(r)
	if h.Embedding != nil {
		h.Embedding.RegisterRoutes(r)
	}
	if h.Chat != nil {
		h.Chat.RegisterRoutes(r)
	}
}

// apiVersionHeader injects X-API-Version into every response of a version group.
func apiVersionHeader(version string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		c.Set("X-API-Version", version)
		return c.Next()
	}
}
