package handler

// ── Search ───────────────────────────────────────────────────────────────────

// FoodItem is one food row returned in search results.
type FoodItem struct {
	ID       uint    `json:"id"`
	NameTh   string  `json:"name_th"`
	NameEn   string  `json:"name_en"`
	EnergyKcal *float64 `json:"energy_kcal"`
	WeightG  *float64 `json:"weight_g"`
	Source   string  `json:"source"`
}

// SearchFoodResponse is the paginated search response.
type SearchFoodResponse struct {
	Data  []FoodItem `json:"data"`
	Total int64      `json:"total"`
	Page  int        `json:"page"`
	Limit int        `json:"limit"`
}

// ── Food Detail ──────────────────────────────────────────────────────────────

// FoodDetailResponse is the full food record with all nutrients.
type FoodDetailResponse struct {
	ID         uint           `json:"id"`
	NameTh     string         `json:"name_th"`
	NameEn     string         `json:"name_en"`
	EnergyKcal *float64       `json:"energy_kcal"`
	WeightG    *float64       `json:"weight_g"`
	Source     string         `json:"source"`
	Nutrients  []NutrientItem `json:"nutrients"`
}

// ── Calc Kcal ────────────────────────────────────────────────────────────────

// IngredientInput is one ingredient entry in the kcal calculation request.
type IngredientInput struct {
	FoodID  uint    `json:"food_id"`
	WeightG float64 `json:"weight_g"`
}

// CalcKcalRequest is the request body for POST /foods/kcal.
type CalcKcalRequest struct {
	Ingredients []IngredientInput `json:"ingredients"`
}

// NutrientItem is one nutrient entry scaled to the requested weight.
type NutrientItem struct {
	NutrientID uint    `json:"nutrient_id"`
	NameTh     string  `json:"name_th"`
	NameEn     string  `json:"name_en"`
	Type       string  `json:"type,omitempty"`
	Amount     float64 `json:"amount"`
	Unit       string  `json:"unit"`
	Operator   string  `json:"operator,omitempty"`
}

// KcalItemResponse is one line in the kcal breakdown.
type KcalItemResponse struct {
	FoodID  uint    `json:"food_id"`
	NameTh  string  `json:"name_th"`
	NameEn  string  `json:"name_en"`
	WeightG float64 `json:"weight_g"`
	Kcal    float64 `json:"kcal"`
}

// CalcKcalResponse is the response body for POST /foods/kcal.
// Nutrients are merged and summed across all items.
type CalcKcalResponse struct {
	TotalKcal float64            `json:"total_kcal"`
	Items     []KcalItemResponse `json:"items"`
	Nutrients []NutrientItem     `json:"nutrients"`
}

// ── Error ─────────────────────────────────────────────────────────────────────

// ErrorResponse is returned on any API error.
type ErrorResponse struct {
	Error string `json:"error"`
}
