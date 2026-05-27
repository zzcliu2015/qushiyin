from fastapi import APIRouter

from app.api.routes import health, jobs, links, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(links.router, prefix="/api/links", tags=["links"])
api_router.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
api_router.include_router(sources.router, prefix="/api/sources", tags=["sources"])
