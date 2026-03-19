package handler

import (
	"open-ingredient/api/internal/domain/food"

	"github.com/gofiber/fiber/v2"
)

// FoodHandler is the Fiber driving adapter for food use cases.
type FoodHandler struct {
	svc *food.Service
}

func NewFoodHandler(svc *food.Service) *FoodHandler {
	return &FoodHandler{svc: svc}
}

// RegisterRoutes attaches all food routes to the given Fiber router.
func (h *FoodHandler) RegisterRoutes(r fiber.Router) {
	foods := r.Group("/foods")
	foods.Get("/search", h.Search)
	foods.Get("/:id", h.GetByID)
	foods.Post("/kcal", h.CalcKcal)
}

// GetByID godoc
//
//	@Summary		Get food detail
//	@Description	Get a single food item with all its nutrients by ID.
//	@Tags			foods
//	@Produce		json
//	@Param			id	path		int	true	"Food ID"
//	@Success		200	{object}	FoodDetailResponse
//	@Header			200	{string}	X-API-Version	"API version"
//	@Failure		400	{object}	ErrorResponse	"Invalid ID"
//	@Failure		404	{object}	ErrorResponse	"Food not found"
//	@Failure		500	{object}	ErrorResponse
//	@Router			/foods/{id} [get]
func (h *FoodHandler) GetByID(c *fiber.Ctx) error {
	id, err := c.ParamsInt("id")
	if err != nil || id <= 0 {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "invalid food id"})
	}

	f, err := h.svc.GetByID(c.Context(), uint(id))
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(ErrorResponse{Error: "food not found"})
	}

	nutrients := make([]NutrientItem, len(f.Nutrients))
	for i, n := range f.Nutrients {
		nutrients[i] = NutrientItem{
			NutrientID: n.NutrientID,
			NameTh:     n.NameTh,
			NameEn:     n.NameEn,
			Type:       n.Type,
			Amount:     n.Amount,
			Unit:       n.Unit,
			Operator:   n.Operator,
		}
	}

	return c.JSON(FoodDetailResponse{
		ID:         f.ID,
		NameTh:     derefStr(f.NameTh),
		NameEn:     derefStr(f.NameEn),
		EnergyKcal: f.Energy,
		WeightG:    f.Weight,
		Source:     derefStr(f.Source),
		Nutrients:  nutrients,
	})
}

// Search godoc
//
//	@Summary		Search foods
//	@Description	Search ingredients/foods by Thai or English name. Returns paginated results.
//	@Tags			foods
//	@Produce		json
//	@Param			q		query		string	false	"Search keyword (Thai or English name)"	example(ข้าว)
//	@Param			page	query		int		false	"Page number"							minimum(1)	default(1)
//	@Param			limit	query		int		false	"Items per page"						minimum(1)	maximum(100)	default(20)
//	@Success		200		{object}	SearchFoodResponse
//	@Header			200		{string}	X-API-Version	"API version"
//	@Failure		500		{object}	ErrorResponse
//	@Router			/foods/search [get]
func (h *FoodHandler) Search(c *fiber.Ctx) error {
	params := food.SearchParams{
		Query: c.Query("q"),
		Page:  c.QueryInt("page", 1),
		Limit: c.QueryInt("limit", 20),
	}

	result, err := h.svc.Search(c.Context(), params)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Error: err.Error()})
	}

	items := make([]FoodItem, len(result.Foods))
	for i, f := range result.Foods {
		items[i] = FoodItem{
			ID:         f.ID,
			NameTh:     derefStr(f.NameTh),
			NameEn:     derefStr(f.NameEn),
			EnergyKcal: f.Energy,
			WeightG:    f.Weight,
			Source:     derefStr(f.Source),
		}
	}

	return c.JSON(SearchFoodResponse{
		Data:  items,
		Total: result.Total,
		Page:  params.Page,
		Limit: params.Limit,
	})
}

// CalcKcal godoc
//
//	@Summary		Calculate kilocalories
//	@Description	Calculate total kcal from a list of ingredients with specified weights in grams. Nutrients are merged and summed across all items.
//	@Tags			foods
//	@Accept			json
//	@Produce		json
//	@Param			request	body		CalcKcalRequest	true	"Ingredient list with weights (weight_g > 0)"
//	@Success		200		{object}	CalcKcalResponse
//	@Header			200		{string}	X-API-Version	"API version"
//	@Failure		400		{object}	ErrorResponse	"Invalid body or weight_g ≤ 0"
//	@Failure		404		{object}	ErrorResponse	"food_id not found"
//	@Failure		500		{object}	ErrorResponse
//	@Router			/foods/kcal [post]
func (h *FoodHandler) CalcKcal(c *fiber.Ctx) error {
	var req CalcKcalRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "invalid request body"})
	}
	if len(req.Ingredients) == 0 {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "ingredients must not be empty"})
	}

	ingredients := make([]food.IngredientWeight, len(req.Ingredients))
	for i, ing := range req.Ingredients {
		if ing.FoodID == 0 {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "food_id must be greater than 0"})
		}
		if ing.WeightG <= 0 {
			return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Error: "weight_g must be greater than 0"})
		}
		ingredients[i] = food.IngredientWeight{
			FoodID:  ing.FoodID,
			WeightG: ing.WeightG,
		}
	}

	result, err := h.svc.CalcKcal(c.Context(), ingredients)
	if err != nil {
		// food not found is a client error
		return c.Status(fiber.StatusNotFound).JSON(ErrorResponse{Error: err.Error()})
	}

	items := make([]KcalItemResponse, len(result.Items))
	for i, item := range result.Items {
		items[i] = KcalItemResponse{
			FoodID:  item.FoodID,
			NameTh:  item.NameTh,
			NameEn:  item.NameEn,
			WeightG: item.WeightG,
			Kcal:    item.Kcal,
		}
	}

	nutrients := make([]NutrientItem, len(result.Nutrients))
	for i, n := range result.Nutrients {
		nutrients[i] = NutrientItem{
			NutrientID: n.NutrientID,
			NameTh:     n.NameTh,
			NameEn:     n.NameEn,
			Type:       n.Type,
			Amount:     n.Amount,
			Unit:       n.Unit,
			Operator:   n.Operator,
		}
	}

	return c.JSON(CalcKcalResponse{
		TotalKcal: result.TotalKcal,
		Items:     items,
		Nutrients: nutrients,
	})
}

func derefStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}
