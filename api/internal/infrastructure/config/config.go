package config

import (
	"fmt"
	"os"
)

type Config struct {
	DBHost     string
	DBPort     string
	DBUser     string
	DBPassword string
	DBName     string
	ServerPort string

	// Embedding — works with Ollama (default) or any OpenAI-compatible API.
	EmbeddingBaseURL string // e.g. "http://ollama:11434" or "https://api.openai.com"
	EmbeddingModel   string // e.g. "nomic-embed-text" or "text-embedding-3-small"
	EmbeddingAPIKey  string // optional; leave empty for Ollama

	// LLM — Ollama chat model for RAG responses.
	LLMModel string // e.g. "llama3.2"
}

func Load() Config {
	return Config{
		DBHost:     getEnv("POSTGRES_HOST", "localhost"),
		DBPort:     getEnv("POSTGRES_PORT", "5432"),
		DBUser:     getEnv("POSTGRES_USER", "postgres"),
		DBPassword: getEnv("POSTGRES_PASSWORD", "postgres"),
		DBName:     getEnv("POSTGRES_DB", "open_ingredient"),
		ServerPort: getEnv("SERVER_PORT", "3000"),

		EmbeddingBaseURL: getEnv("EMBEDDING_BASE_URL", "http://localhost:11434"),
		EmbeddingModel:   getEnv("EMBEDDING_MODEL", "nomic-embed-text"),
		EmbeddingAPIKey:  getEnv("EMBEDDING_API_KEY", ""),

		LLMModel: getEnv("LLM_MODEL", "llama3.2"),
	}
}

func (c Config) DSN() string {
	return fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=disable TimeZone=Asia/Bangkok",
		c.DBHost, c.DBPort, c.DBUser, c.DBPassword, c.DBName,
	)
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
