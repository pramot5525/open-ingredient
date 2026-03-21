// Package embedding provides an HTTP embedder compatible with any
// OpenAI-style embeddings API (OpenAI, Ollama /v1/embeddings, etc.).
package embedding

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

// HTTPEmbedder calls any OpenAI-compatible /v1/embeddings endpoint.
type HTTPEmbedder struct {
	baseURL string
	model   string
	apiKey  string // optional — leave empty for Ollama
	client  *http.Client
}

// NewHTTPEmbedder creates an embedder pointing at baseURL.
// Set apiKey to "" when no authentication is needed (e.g. Ollama).
func NewHTTPEmbedder(baseURL, model, apiKey string) *HTTPEmbedder {
	return &HTTPEmbedder{
		baseURL: strings.TrimRight(baseURL, "/"),
		model:   model,
		apiKey:  apiKey,
		client:  &http.Client{},
	}
}

func (e *HTTPEmbedder) Model() string { return e.model }

type embedRequest struct {
	Input string `json:"input"`
	Model string `json:"model"`
}

type embedResponse struct {
	Data []struct {
		Embedding []float32 `json:"embedding"`
	} `json:"data"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error"`
}

func (e *HTTPEmbedder) Embed(ctx context.Context, text string) ([]float32, error) {
	body, err := json.Marshal(embedRequest{Input: text, Model: e.model})
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		e.baseURL+"/v1/embeddings", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	if e.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+e.apiKey)
	}

	resp, err := e.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result embedResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	if result.Error != nil {
		return nil, fmt.Errorf("embedder: %s", result.Error.Message)
	}
	if len(result.Data) == 0 {
		return nil, fmt.Errorf("embedder: empty response from %s", e.baseURL)
	}
	return result.Data[0].Embedding, nil
}

// NewOpenAIEmbedder is kept for backwards-compatibility.
// Prefer NewHTTPEmbedder for explicit configuration.
func NewOpenAIEmbedder(apiKey string) *HTTPEmbedder {
	return NewHTTPEmbedder("https://api.openai.com", "text-embedding-3-small", apiKey)
}
