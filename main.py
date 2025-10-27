import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import db, create_document, get_documents
from schemas import Product

app = FastAPI(title="ShopEase API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "ShopEase backend running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# E-commerce: Products endpoints
class ProductOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool


@app.get("/api/products", response_model=List[ProductOut])
def list_products(category: Optional[str] = Query(default=None), q: Optional[str] = Query(default=None)):
    """List products with optional category and search query"""
    filter_dict = {}
    if category:
        filter_dict["category"] = category
    if q:
        # simple regex search on title or description
        filter_dict["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    docs = get_documents("product", filter_dict)
    out: List[ProductOut] = []
    for d in docs:
        out.append(
            ProductOut(
                id=str(d.get("_id")),
                title=d.get("title"),
                description=d.get("description"),
                price=float(d.get("price", 0)),
                category=d.get("category"),
                in_stock=bool(d.get("in_stock", True)),
            )
        )
    return out


@app.post("/api/products", status_code=201)
def create_product(product: Product):
    """Create a new product"""
    try:
        inserted_id = create_document("product", product)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/categories", response_model=List[str])
def list_categories():
    """Return distinct product categories"""
    try:
        categories = db["product"].distinct("category") if db is not None else []
        categories.sort()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed")
def seed_products():
    """Seed sample products if none exist"""
    try:
        count = db["product"].count_documents({}) if db is not None else 0
        if count > 0:
            return {"status": "ok", "seeded": False, "existing": count}
        samples = [
            {
                "title": "Classic White T-Shirt",
                "description": "Soft cotton tee for everyday wear.",
                "price": 14.99,
                "category": "Clothes",
                "in_stock": True,
            },
            {
                "title": "Organic Granola",
                "description": "Crunchy, honey-sweetened breakfast granola.",
                "price": 7.49,
                "category": "Food",
                "in_stock": True,
            },
            {
                "title": "Bluetooth Headphones",
                "description": "Noise-isolating on-ear headphones with 20h battery.",
                "price": 59.99,
                "category": "Electronics",
                "in_stock": True,
            },
            {
                "title": "Stainless Water Bottle",
                "description": "Keeps drinks cold for 24h and hot for 12h.",
                "price": 19.99,
                "category": "Home",
                "in_stock": True,
            },
            {
                "title": "Gourmet Dark Chocolate",
                "description": "70% cacao premium chocolate bar.",
                "price": 3.99,
                "category": "Food",
                "in_stock": True,
            },
        ]
        for s in samples:
            create_document("product", s)
        return {"status": "ok", "seeded": True, "count": len(samples)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
