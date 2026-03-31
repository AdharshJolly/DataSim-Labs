from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import router as dataset_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.semantic_rules import router as semantic_rules_router
from app.api.errors import register_exception_handlers
from app.auth.routes import router as auth_router
from app.core.config import settings
from app.db.init_db import init_db

app = FastAPI(title=settings.app_name)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(dataset_router, prefix=settings.api_prefix)
app.include_router(semantic_rules_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup_init_indexes() -> None:
    init_db()
