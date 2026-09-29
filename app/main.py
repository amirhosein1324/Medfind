from fastapi import FastAPI
<<<<<<< HEAD

from .database import Base, engine
from .routers import auth, medicines, pharmacies, search, users

=======
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from fastapi.middleware.cors import CORSMiddleware

from .config import get_cors_origins
from .database import Base, engine
from .logging_config import configure_logging
from .middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from .rate_limit import limiter
from .routers import auth, medicines, pharmacies, search, users

configure_logging()

>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
# NOTE: create_all() is fine for development. For production, replace this
# with Alembic migrations (see README).
Base.metadata.create_all(bind=engine)

<<<<<<< HEAD
app = FastAPI(
    title="MedFind API",
    description="Smart Medicine Search and Pharmacy Comparison Platform",
    version="1.0.0",
)

=======
API_VERSION = "1.1.0"

app = FastAPI(
    title="MedFind API",
    description="Smart Medicine Search and Pharmacy Comparison Platform",
    version=API_VERSION,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(medicines.router, prefix="/api/medicines", tags=["Medicines"])
app.include_router(pharmacies.router, prefix="/api/pharmacies", tags=["Pharmacies"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])


@app.get("/")
def root():
    return {"message": "Welcome to MedFind API", "docs": "/docs"}
<<<<<<< HEAD
=======


@app.get("/health", tags=["Meta"])
def health_check():
    """Liveness/readiness probe for load balancers and uptime monitors."""
    return {"status": "ok"}


@app.get("/version", tags=["Meta"])
def version():
    return {"version": API_VERSION}
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
