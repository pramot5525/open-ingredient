package repository

import (
	"context"
	"open-ingredient/api/internal/domain/food"

	"gorm.io/gorm"
)

// ── GORM models ───────────────────────────────────────────────────────────────

type unitModel struct {
	ID     uint    `gorm:"primaryKey;column:id"`
	NameTh *string `gorm:"column:name_th"`
	NameEn *string `gorm:"column:name_en"`
}

func (unitModel) TableName() string { return "units" }

type nutrientModel struct {
	ID       uint    `gorm:"primaryKey;column:id"`
	NameTh   *string `gorm:"column:name_th"`
	NameEn   *string `gorm:"column:name_en"`
	Type     *string `gorm:"column:type"`
	ParentID *uint   `gorm:"column:parent_id"`
}

func (nutrientModel) TableName() string { return "nutrients" }

type foodNutrientModel struct {
	FoodID     uint          `gorm:"primaryKey;column:food_id"`
	NutrientID uint          `gorm:"primaryKey;column:nutrient_id"`
	Amount     *float64      `gorm:"column:amount"`
	UnitID     *uint         `gorm:"column:unit_id"`
	Operator   *string       `gorm:"column:operator"`
	Nutrient   nutrientModel `gorm:"foreignKey:NutrientID;references:ID"`
	Unit       unitModel     `gorm:"foreignKey:UnitID;references:ID"`
}

func (foodNutrientModel) TableName() string { return "food_nutrients" }

type foodModel struct {
	ID            uint                `gorm:"primaryKey;column:id"`
	NameTh        *string             `gorm:"column:name_th"`
	NameEn        *string             `gorm:"column:name_en"`
	CategoryID    *uint               `gorm:"column:category_id"`
	Weight        *float64            `gorm:"column:weight"`
	WeightUnit    *uint               `gorm:"column:weight_unit"`
	Energy        *float64            `gorm:"column:energy"`
	EnergyUnit    *uint               `gorm:"column:energy_unit"`
	IsRecipe      bool                `gorm:"column:is_recipe"`
	Source        *string             `gorm:"column:source"`
	SourceID      *string             `gorm:"column:source_id"`
	FoodNutrients []foodNutrientModel `gorm:"foreignKey:FoodID"`
}

func (foodModel) TableName() string { return "foods" }

// ── Repository ────────────────────────────────────────────────────────────────

type FoodRepository struct {
	db *gorm.DB
}

func NewFoodRepository(db *gorm.DB) *FoodRepository {
	return &FoodRepository{db: db}
}

func (r *FoodRepository) Search(ctx context.Context, params food.SearchParams) (food.SearchResult, error) {
	query := r.db.WithContext(ctx).Model(&foodModel{})

	if params.Query != "" {
		like := "%" + params.Query + "%"
		query = query.Where("name_th ILIKE ? OR name_en ILIKE ?", like, like)
	}

	var total int64
	if err := query.Count(&total).Error; err != nil {
		return food.SearchResult{}, err
	}

	var models []foodModel
	offset := (params.Page - 1) * params.Limit
	if err := query.Offset(offset).Limit(params.Limit).Find(&models).Error; err != nil {
		return food.SearchResult{}, err
	}

	foods := make([]food.Food, len(models))
	for i, m := range models {
		foods[i] = toDomain(m)
	}
	return food.SearchResult{Foods: foods, Total: total}, nil
}

func (r *FoodRepository) FindByID(ctx context.Context, id uint) (*food.Food, error) {
	var m foodModel
	err := r.db.WithContext(ctx).
		Preload("FoodNutrients", "amount IS NOT NULL AND amount <> 0").
		Preload("FoodNutrients.Nutrient").
		Preload("FoodNutrients.Unit").
		First(&m, id).Error
	if err != nil {
		return nil, err
	}
	f := toDomain(m)
	return &f, nil
}

func (r *FoodRepository) FindByIDs(ctx context.Context, ids []uint) ([]food.Food, error) {
	var models []foodModel
	err := r.db.WithContext(ctx).
		Preload("FoodNutrients", "amount IS NOT NULL AND amount <> 0").
		Preload("FoodNutrients.Nutrient").
		Preload("FoodNutrients.Unit").
		Where("id IN ?", ids).
		Find(&models).Error
	if err != nil {
		return nil, err
	}

	foods := make([]food.Food, len(models))
	for i, m := range models {
		foods[i] = toDomain(m)
	}
	return foods, nil
}

// ── Mapping ───────────────────────────────────────────────────────────────────

func toDomain(m foodModel) food.Food {
	nutrients := make([]food.FoodNutrient, len(m.FoodNutrients))
	for i, fn := range m.FoodNutrients {
		nutrients[i] = food.FoodNutrient{
			NutrientID: fn.NutrientID,
			NameTh:     derefStr(fn.Nutrient.NameTh),
			NameEn:     derefStr(fn.Nutrient.NameEn),
			Type:       derefStr(fn.Nutrient.Type),
			Amount:     derefFloat(fn.Amount),
			Unit:       derefStr(fn.Unit.NameEn),
			Operator:   derefStr(fn.Operator),
		}
	}
	return food.Food{
		ID:         m.ID,
		NameTh:     m.NameTh,
		NameEn:     m.NameEn,
		CategoryID: m.CategoryID,
		Weight:     m.Weight,
		Energy:     m.Energy,
		IsRecipe:   m.IsRecipe,
		Source:     m.Source,
		SourceID:   m.SourceID,
		Nutrients:  nutrients,
	}
}

func derefStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

func derefFloat(f *float64) float64 {
	if f == nil {
		return 0
	}
	return *f
}
