// Package chat implements the RAG-based food nutrition chat use-case.
package chat

import (
	"context"
	"fmt"
	"open-ingredient/api/internal/domain/embedding"
	"open-ingredient/api/internal/domain/food"
	"strings"
)

// LLM is the port for any text-generation model.
type LLM interface {
	Generate(ctx context.Context, prompt string) (string, error)
	Model() string
}

// Result is the structured output of a chat turn.
type Result struct {
	Reply   string
	Sources []embedding.SimilarFood
}

// Service orchestrates the RAG pipeline:
// query → vector search → nutrient lookup → LLM → reply.
type Service struct {
	embSvc   *embedding.Service
	foodRepo food.Repository
	llm      LLM
}

func NewService(embSvc *embedding.Service, foodRepo food.Repository, llm LLM) *Service {
	return &Service{embSvc: embSvc, foodRepo: foodRepo, llm: llm}
}

// Chat answers a free-text nutrition question using RAG.
func (s *Service) Chat(ctx context.Context, message string) (Result, error) {
	// 1. Semantic search
	similar, err := s.embSvc.SemanticSearch(ctx, message, 5)
	if err != nil {
		return Result{}, fmt.Errorf("vector search: %w", err)
	}
	if len(similar) == 0 {
		return Result{Reply: "ไม่พบข้อมูลอาหารที่เกี่ยวข้องในฐานข้อมูล"}, nil
	}

	// 2. Load full nutrient data for matched foods
	ids := make([]uint, len(similar))
	for i, f := range similar {
		ids[i] = f.FoodID
	}
	foods, err := s.foodRepo.FindByIDs(ctx, ids)
	if err != nil {
		return Result{}, fmt.Errorf("food lookup: %w", err)
	}

	// 3. Build RAG prompt
	prompt := buildPrompt(message, foods)

	// 4. Generate answer
	reply, err := s.llm.Generate(ctx, prompt)
	if err != nil {
		return Result{}, fmt.Errorf("llm generate: %w", err)
	}

	return Result{Reply: reply, Sources: similar}, nil
}

// buildPrompt constructs the RAG prompt from matched foods and their nutrients.
func buildPrompt(question string, foods []food.Food) string {
	var sb strings.Builder

	sb.WriteString("คุณคือผู้ช่วยด้านโภชนาการอาหารไทย ตอบคำถามเกี่ยวกับแคลอรี่และสารอาหารโดยอ้างอิงข้อมูลต่อไปนี้เท่านั้น\n\n")
	sb.WriteString("=== ข้อมูลอาหารจากฐานข้อมูล ===\n")

	for i, f := range foods {
		nameTh := "-"
		if f.NameTh != nil {
			nameTh = *f.NameTh
		}
		nameEn := ""
		if f.NameEn != nil {
			nameEn = " (" + *f.NameEn + ")"
		}
		baseW := 100.0
		if f.Weight != nil && *f.Weight > 0 {
			baseW = *f.Weight
		}

		sb.WriteString(fmt.Sprintf("\n%d. %s%s — ต่อ %.0f g\n", i+1, nameTh, nameEn, baseW))

		if f.Energy != nil {
			sb.WriteString(fmt.Sprintf("   พลังงาน: %.1f kcal\n", *f.Energy))
		}

		macros := []string{"Protein", "Total lipid (fat)", "Carbohydrate, by difference", "Fiber, total dietary", "Sugars, total"}
		for _, n := range f.Nutrients {
			for _, m := range macros {
				if strings.EqualFold(n.NameEn, m) {
					sb.WriteString(fmt.Sprintf("   %s: %.2f %s\n", n.NameEn, n.Amount, n.Unit))
				}
			}
		}
	}

	sb.WriteString("\n=== คำถาม ===\n")
	sb.WriteString(question)
	sb.WriteString("\n\nตอบเป็นภาษาไทย กระชับ และระบุตัวเลขแคลอรี่ชัดเจน")

	return sb.String()
}
