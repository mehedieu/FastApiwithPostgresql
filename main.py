import os
from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, ConfigDict, Field

from sqlalchemy import (
    create_engine,
    String,
    Float,
    Integer,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

load_dotenv()
# -------------------------
# Database configuration
# -------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required"
    )

# Support Render PostgreSQL connection URLs.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1,
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# -------------------------
# SQLAlchemy model
# -------------------------

class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )


# -------------------------
# Pydantic schemas
# -------------------------

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, allow_inf_nan=False)
    description: str = Field(
        min_length=1,
        max_length=500,
    )


class ProductUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, allow_inf_nan=False)
    description: str = Field(
        min_length=1,
        max_length=500,
    )


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# FastAPI application
# -------------------------

app = FastAPI(
    title="Product CRUD API",
    version="1.0.0",
)


# -------------------------
# CORS configuration
# -------------------------

allowed_origins = [
    "http://localhost:5173",
]

frontend_url = os.getenv("FRONTEND_URL")

if frontend_url:
    allowed_origins.append(frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


# -------------------------
# Database dependency
# -------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# For this tutorial only.
# Use Alembic migrations in production.

Base.metadata.create_all(bind=engine)


# -------------------------
# Health endpoint
# -------------------------

@app.get("/health")
def health_check():
    return {"status": "ok"}


# -------------------------
# CREATE
# -------------------------

@app.post(
    "/products/",
    response_model=ProductResponse,
    status_code=201,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
):
    product = Product(
        name=product_data.name,
        price=product_data.price,
        description=product_data.description,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


# -------------------------
# READ ALL
# -------------------------

@app.get(
    "/products/",
    response_model=list[ProductResponse],
)
def get_products(
    db: Session = Depends(get_db),
):
    statement = select(Product).order_by(Product.id)

    return db.scalars(statement).all()


# -------------------------
# READ ONE
# -------------------------

@app.get(
    "/products/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


# -------------------------
# UPDATE
# -------------------------

@app.put(
    "/products/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    product.name = product_data.name
    product.price = product_data.price
    product.description = product_data.description

    db.commit()
    db.refresh(product)

    return product


# -------------------------
# DELETE
# -------------------------

@app.delete(
    "/products/{product_id}",
    status_code=204,
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    db.delete(product)
    db.commit()

    return Response(status_code=204)