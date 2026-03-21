package embedding

// FoodEmbedding is the domain representation of one embedded food record.
type FoodEmbedding struct {
	ID     uint
	FoodID uint
	Text   string    // text that was embedded (e.g. "ข้าวมันไก่ Chicken Rice")
	Vector []float32 // embedding vector from the model
	Model  string    // e.g. "text-embedding-3-small"
}

// SimilarFood is one result from a semantic similarity search.
type SimilarFood struct {
	FoodID     uint
	NameTh     string
	NameEn     string
	Similarity float64 // cosine similarity in [0,1]; higher = more similar
}
