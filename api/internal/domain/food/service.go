package food

import (
	"context"
	"fmt"
)

// IngredientWeight pairs a food ID with the desired weight in grams.
type IngredientWeight struct {
	FoodID  uint
	WeightG float64
}

// KcalItem is one line of the kcal calculation result.
type KcalItem struct {
	FoodID  uint
	NameTh  string
	NameEn  string
	WeightG float64
	Kcal    float64
}

// KcalResult is the full kcal calculation response.
// Nutrients are merged across all items and summed by nutrient_id.
type KcalResult struct {
	TotalKcal float64
	Items     []KcalItem
	Nutrients []FoodNutrient
}

// Service holds all use cases related to foods.
type Service struct {
	repo Repository
}

func NewService(repo Repository) *Service {
	return &Service{repo: repo}
}

// GetByID returns a single food with all its nutrients.
func (s *Service) GetByID(ctx context.Context, id uint) (*Food, error) {
	return s.repo.FindByID(ctx, id)
}

// Search delegates to the repository with validated pagination defaults.
func (s *Service) Search(ctx context.Context, params SearchParams) (SearchResult, error) {
	if params.Page < 1 {
		params.Page = 1
	}
	switch {
	case params.Limit < 1:
		params.Limit = 20
	case params.Limit > 100:
		params.Limit = 100
	}
	return s.repo.Search(ctx, params)
}

// CalcKcal fetches foods by ID and computes kilocalories scaled to each requested weight.
func (s *Service) CalcKcal(ctx context.Context, ingredients []IngredientWeight) (KcalResult, error) {
	if len(ingredients) == 0 {
		return KcalResult{}, nil
	}

	ids := make([]uint, len(ingredients))
	for i, ing := range ingredients {
		ids[i] = ing.FoodID
	}

	foods, err := s.repo.FindByIDs(ctx, ids)
	if err != nil {
		return KcalResult{}, err
	}

	foodMap := make(map[uint]Food, len(foods))
	for _, f := range foods {
		foodMap[f.ID] = f
	}

	items := make([]KcalItem, 0, len(ingredients))
	var total float64
	merged := make(map[uint]*FoodNutrient)

	for _, ing := range ingredients {
		f, ok := foodMap[ing.FoodID]
		if !ok {
			return KcalResult{}, fmt.Errorf("food_id %d not found", ing.FoodID)
		}
		kcal := f.KcalFor(ing.WeightG)
		total += kcal
		items = append(items, KcalItem{
			FoodID:  f.ID,
			NameTh:  derefStr(f.NameTh),
			NameEn:  derefStr(f.NameEn),
			WeightG: ing.WeightG,
			Kcal:    kcal,
		})
		for _, n := range f.ScaleNutrients(ing.WeightG) {
			if existing, ok := merged[n.NutrientID]; ok {
				existing.Amount += n.Amount
			} else {
				copy := n
				merged[n.NutrientID] = &copy
			}
		}
	}

	nutrients := make([]FoodNutrient, 0, len(merged))
	for _, n := range merged {
		n.Amount = round2(n.Amount)
		nutrients = append(nutrients, *n)
	}

	return KcalResult{TotalKcal: total, Items: items, Nutrients: nutrients}, nil
}

func derefStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}
