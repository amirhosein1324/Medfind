from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import auth, medicines, pharmacies, search, users

# NOTE: create_all() is fine for development. For production, replace this
# with Alembic migrations (see README).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MedFind API",
    description="Smart Medicine Search and Pharmacy Comparison Platform",
    version="1.0.0",
)

# Allows a separately-served frontend (e.g. the plain HTML/CSS/JS dashboard
# in /frontend) to call this API from a different origin during development.
# Tighten allow_origins to your real frontend's domain before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(medicines.router, prefix="/api/medicines", tags=["Medicines"])
app.include_router(pharmacies.router, prefix="/api/pharmacies", tags=["Pharmacies"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])


@app.get("/")
def root():
    return {"message": "Welcome to MedFind API", "docs": "/docs"}
