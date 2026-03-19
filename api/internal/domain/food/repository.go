package food

import "context"

// SearchParams holds pagination and filter options for food search.
type SearchParams struct {
	Query string
	Page  int
	Limit int
}

// SearchResult is the paginated result from a search query.
type SearchResult struct {
	Foods []Food
	Total int64
}

// Repository is the port (interface) that driven adapters must implement.
type Repository interface {
	Search(ctx context.Context, params SearchParams) (SearchResult, error)
	FindByID(ctx context.Context, id uint) (*Food, error)
	FindByIDs(ctx context.Context, ids []uint) ([]Food, error)
}
