from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import get_settings
from app.database.mongodb import mongodb
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.companies import router as companies_router
from app.api.simulation import router as simulation_router
from app.api.boardroom import router as boardroom_router
from app.api.decisions import router as decisions_router
from app.api.experiments import router as experiments_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Starting FounderVerse backend...")

    mongodb.connect()

    yield

    print("Shutting down FounderVerse backend...")

    mongodb.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(simulation_router)
app.include_router(boardroom_router)
app.include_router(decisions_router)
app.include_router(experiments_router)

@app.get("/")
async def root():
    return {
        "name": "FounderVerse",
        "version": settings.app_version,
        "status": "running",
    }