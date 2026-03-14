from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.dataset import router as dataset_router
from app.api.v1.routes.health import router as health_router
from app.auth.routes import router as auth_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(dataset_router, prefix=settings.api_prefix)
