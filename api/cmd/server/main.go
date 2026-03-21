// @title           Open Ingredient API
// @version         1.0
// @description     REST API for searching food ingredients and calculating kilocalories.
// @termsOfService  http://swagger.io/terms/

// @contact.name   Open Ingredient
// @contact.url    https://github.com/open-ingredient

// @license.name  MIT

// @host      localhost:3000
// @BasePath  /api/v1

// @externalDocs.description  OpenAPI
// @externalDocs.url          https://swagger.io/resources/open-api/
package main

import (
	"log"
	"open-ingredient/api/docs"
	"open-ingredient/api/internal/adapter/handler"
	"open-ingredient/api/internal/adapter/repository"
	"open-ingredient/api/internal/adapter/router"
	"open-ingredient/api/internal/domain/chat"
	"open-ingredient/api/internal/domain/embedding"
	"open-ingredient/api/internal/domain/food"
	"open-ingredient/api/internal/infrastructure/config"
	"open-ingredient/api/internal/infrastructure/db"
	infraEmbedding "open-ingredient/api/internal/infrastructure/embedding"
	"open-ingredient/api/internal/infrastructure/llm"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	fiberSwagger "github.com/gofiber/swagger"
	"github.com/joho/godotenv"
)

func main() {
	// Load .env if present (local dev). In Docker, env vars come from Compose.
	if err := godotenv.Load(".env"); err != nil {
		log.Println("no .env file found, using environment variables")
	}

	cfg := config.Load()

	gormDB, err := db.NewPostgres(cfg)
	if err != nil {
		log.Fatalf("failed to connect to database: %v", err)
	}

	// Wire food dependencies
	foodRepo := repository.NewFoodRepository(gormDB)
	foodSvc := food.NewService(foodRepo)

	// Wire embedding dependencies
	embedder := infraEmbedding.NewHTTPEmbedder(cfg.EmbeddingBaseURL, cfg.EmbeddingModel, cfg.EmbeddingAPIKey)
	embeddingRepo := repository.NewEmbeddingRepository(gormDB)
	embeddingSvc := embedding.NewService(embeddingRepo, embedder)
	embeddingHandler := handler.NewEmbeddingHandler(embeddingSvc)
	log.Printf("semantic search enabled: model=%s base=%s", cfg.EmbeddingModel, cfg.EmbeddingBaseURL)

	// Wire chat (RAG) dependencies
	ollamaLLM := llm.NewOllamaLLM(cfg.EmbeddingBaseURL, cfg.LLMModel)
	chatSvc := chat.NewService(embeddingSvc, foodRepo, ollamaLLM)
	chatHandler := handler.NewChatHandler(chatSvc)
	log.Printf("rag chat enabled: llm=%s", cfg.LLMModel)

	app := fiber.New(fiber.Config{
		AppName: "Open Ingredient API",
	})

	app.Use(recover.New())
	app.Use(cors.New())
	app.Use(logger.New())

	// Swagger UI
	docs.SwaggerInfo.BasePath = "/api/v1"
	app.Get("/api/docs/*", fiberSwagger.HandlerDefault)

	// Health check (unversioned)
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})

	// Mount all API versions
	router.Register(app, router.Handlers{
		Food:      handler.NewFoodHandler(foodSvc),
		Embedding: embeddingHandler,
		Chat:      chatHandler,
	})

	log.Printf("starting server on :%s", cfg.ServerPort)
	log.Fatal(app.Listen(":" + cfg.ServerPort))
}
