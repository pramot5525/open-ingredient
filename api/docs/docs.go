// Hand-written OpenAPI 3.0.3 spec.
// Update this file when adding or changing endpoints/schemas.

package docs

import "github.com/swaggo/swag"

const docTemplate = `{
    "openapi": "3.0.3",
    "info": {
        "title": "{{.Title}}",
        "description": "{{escape .Description}}",
        "version": "{{.Version}}",
        "termsOfService": "http://swagger.io/terms/",
        "contact": {
            "name": "Open Ingredient",
            "url": "https://github.com/open-ingredient"
        },
        "license": {"name": "MIT"}
    },
    "servers": [
        {"url": "http://{{.Host}}{{.BasePath}}", "description": "Local development"},
        {"url": "https://{{.Host}}{{.BasePath}}", "description": "Production"}
    ],
    "tags": [
        {
            "name": "foods",
            "description": "Search ingredients, get food detail, and calculate kilocalories"
        }
    ],
    "paths": {
        "/foods/{id}": {
            "get": {
                "summary": "Get food detail",
                "description": "Get a single food item with all its nutrients by ID. Nutrients with NULL or zero values are excluded.",
                "tags": ["foods"],
                "operationId": "getFoodByID",
                "parameters": [
                    {
                        "name": "id", "in": "path", "required": true,
                        "description": "Food ID",
                        "schema": {"type": "integer", "minimum": 1, "example": 17}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Food detail with nutrients",
                        "headers": {
                            "X-API-Version": {
                                "description": "API version",
                                "schema": {"type": "string", "example": "1"}
                            }
                        },
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/FoodDetailResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid ID",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "404": {
                        "description": "Food not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/foods/search": {
            "get": {
                "summary": "Search foods",
                "description": "Search ingredients/foods by Thai or English name. Returns paginated results.",
                "tags": ["foods"],
                "operationId": "searchFoods",
                "parameters": [
                    {
                        "name": "q", "in": "query",
                        "description": "Search keyword (Thai or English name)",
                        "schema": {"type": "string", "example": "ข้าว"}
                    },
                    {
                        "name": "page", "in": "query",
                        "description": "Page number",
                        "schema": {"type": "integer", "minimum": 1, "default": 1}
                    },
                    {
                        "name": "limit", "in": "query",
                        "description": "Items per page (max 100)",
                        "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Paginated food list",
                        "headers": {
                            "X-API-Version": {
                                "description": "API version",
                                "schema": {"type": "string", "example": "1"}
                            }
                        },
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SearchFoodResponse"}
                            }
                        }
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/foods/kcal": {
            "post": {
                "summary": "Calculate kilocalories",
                "description": "Calculate total kcal from a list of ingredients with specified weights in grams. Nutrients are merged and summed across all items. All amounts are rounded to 2 decimal places.",
                "tags": ["foods"],
                "operationId": "calcKcal",
                "requestBody": {
                    "required": true,
                    "description": "Ingredient list with weights (weight_g must be > 0)",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CalcKcalRequest"},
                            "example": {
                                "ingredients": [
                                    {"food_id": 17,   "weight_g": 120},
                                    {"food_id": 1302, "weight_g": 100}
                                ]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Total kcal with per-item breakdown and merged nutrients",
                        "headers": {
                            "X-API-Version": {
                                "description": "API version",
                                "schema": {"type": "string", "example": "1"}
                            }
                        },
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CalcKcalResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid body or weight_g ≤ 0",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "404": {
                        "description": "food_id not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "NutrientItem": {
                "type": "object",
                "properties": {
                    "nutrient_id": {"type": "integer", "example": 3},
                    "name_th":     {"type": "string",  "example": "โปรตีน"},
                    "name_en":     {"type": "string",  "example": "Protein"},
                    "type":        {"type": "string",  "example": "proximate"},
                    "amount": {
                        "type": "number", "example": 12.45,
                        "description": "Scaled to requested weight_g, rounded to 2 decimal places"
                    },
                    "unit": {
                        "type": "string", "example": "g",
                        "enum": ["kcal", "g", "mg", "µg"]
                    },
                    "operator": {
                        "type": "string", "example": "",
                        "enum": ["<", "~", ">", ""],
                        "description": "Precision qualifier"
                    }
                }
            },
            "FoodDetailResponse": {
                "type": "object",
                "properties": {
                    "id":          {"type": "integer", "example": 17},
                    "name_th":     {"type": "string",  "example": "ข้าวเจ้า, นึ่ง"},
                    "name_en":     {"type": "string",  "example": "Rice, polished, steamed"},
                    "energy_kcal": {"type": "number",  "example": 140.0, "description": "kcal per base weight_g"},
                    "weight_g":    {"type": "number",  "example": 100.0, "description": "Base weight in grams"},
                    "source": {
                        "type": "string", "example": "THAIFCD",
                        "enum": ["THAIFCD", "FDC_FOUNDATION", "FDC_SR_LEGACY"]
                    },
                    "nutrients": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/NutrientItem"}
                    }
                }
            },
            "FoodItem": {
                "type": "object",
                "properties": {
                    "id":          {"type": "integer", "example": 17},
                    "name_th":     {"type": "string",  "example": "ข้าวเจ้า, นึ่ง"},
                    "name_en":     {"type": "string",  "example": "Rice, polished, steamed"},
                    "energy_kcal": {"type": "number",  "example": 140.0, "description": "kcal per base weight_g"},
                    "weight_g":    {"type": "number",  "example": 100.0, "description": "Base weight in grams"},
                    "source": {
                        "type": "string", "example": "THAIFCD",
                        "enum": ["THAIFCD", "FDC_FOUNDATION", "FDC_SR_LEGACY"]
                    }
                }
            },
            "SearchFoodResponse": {
                "type": "object",
                "properties": {
                    "data":  {"type": "array", "items": {"$ref": "#/components/schemas/FoodItem"}},
                    "total": {"type": "integer", "example": 120},
                    "page":  {"type": "integer", "example": 1},
                    "limit": {"type": "integer", "example": 20}
                }
            },
            "IngredientInput": {
                "type": "object",
                "required": ["food_id", "weight_g"],
                "properties": {
                    "food_id":  {"type": "integer", "example": 17,    "minimum": 1},
                    "weight_g": {"type": "number",  "example": 120.0, "minimum": 0.01, "description": "Weight in grams"}
                }
            },
            "CalcKcalRequest": {
                "type": "object",
                "required": ["ingredients"],
                "properties": {
                    "ingredients": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"$ref": "#/components/schemas/IngredientInput"}
                    }
                }
            },
            "KcalItemResponse": {
                "type": "object",
                "properties": {
                    "food_id":  {"type": "integer", "example": 17},
                    "name_th":  {"type": "string",  "example": "ข้าวเจ้า, นึ่ง"},
                    "name_en":  {"type": "string",  "example": "Rice, polished, steamed"},
                    "weight_g": {"type": "number",  "example": 120.0},
                    "kcal":     {"type": "number",  "example": 168.0, "description": "Rounded to 2 decimal places"}
                }
            },
            "CalcKcalResponse": {
                "type": "object",
                "properties": {
                    "total_kcal": {
                        "type": "number", "example": 508.0,
                        "description": "Total kcal across all ingredients, rounded to 2 decimal places"
                    },
                    "items": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/KcalItemResponse"}
                    },
                    "nutrients": {
                        "type": "array",
                        "description": "Nutrients merged and summed across all items (NULL/zero values excluded)",
                        "items": {"$ref": "#/components/schemas/NutrientItem"}
                    }
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "food_id 99 not found"}
                }
            }
        }
    }
}`

// SwaggerInfo holds exported Swagger Info so clients can modify it
var SwaggerInfo = &swag.Spec{
	Version:          "1.0",
	Host:             "localhost:3000",
	BasePath:         "/api/v1",
	Schemes:          []string{"http", "https"},
	Title:            "Open Ingredient API",
	Description:      "REST API for searching food ingredients, viewing nutrient detail, and calculating kilocalories from a list of ingredients with weights. Nutrients with NULL or zero values are excluded. All numeric amounts are rounded to 2 decimal places.",
	InfoInstanceName: "swagger",
	SwaggerTemplate:  docTemplate,
	LeftDelim:        "{{",
	RightDelim:       "}}",
}

func init() {
	swag.Register(SwaggerInfo.InstanceName(), SwaggerInfo)
}
