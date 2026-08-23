"""API router aggregation."""

from fastapi import APIRouter

from app.api.routes import auth, candidates, jobs, screening, stats

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(stats.router)
api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
api_router.include_router(screening.router)
