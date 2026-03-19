package food

import "math"

// FoodNutrient holds one nutrient entry for a food, per base weight.
type FoodNutrient struct {
	NutrientID uint
	NameTh     string
	NameEn     string
	Type       string
	Amount     float64 // amount per base weight (foods.weight grams)
	Unit       string  // e.g. g, mg, µg, kcal
	Operator   string  // <, ~, > or empty
}

// Food is the core domain entity representing an ingredient or dish.
// Energy and Weight fields reflect per-base-weight values (typically 100 g).
type Food struct {
	ID         uint
	NameTh     *string
	NameEn     *string
	CategoryID *uint
	Weight     *float64 // base weight in grams (usually 100)
	Energy     *float64 // kcal for base weight
	Source     *string
	SourceID   *string
	Nutrients  []FoodNutrient
}

// KcalFor returns the kilocalories for a given weight in grams.
// Returns 0 if energy or base weight data is missing.
func (f *Food) KcalFor(weightG float64) float64 {
	if f.Energy == nil || f.Weight == nil || *f.Weight == 0 {
		return 0
	}
	return round2((*f.Energy / *f.Weight) * weightG)
}

func round2(v float64) float64 {
	return math.Round(v*100) / 100
}

// ScaleNutrients returns nutrients scaled to the requested weight in grams.
func (f *Food) ScaleNutrients(weightG float64) []FoodNutrient {
	if len(f.Nutrients) == 0 || f.Weight == nil || *f.Weight == 0 {
		return nil
	}
	ratio := weightG / *f.Weight
	out := make([]FoodNutrient, len(f.Nutrients))
	for i, n := range f.Nutrients {
		out[i] = n
		out[i].Amount = round2(n.Amount * ratio)
	}
	return out
}
