"""Aggregates v1 route modules (docs/09 §2)."""
from fastapi import APIRouter

from app.api.v1.routes import admin, agent, auth, nutrition, profile, social

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(nutrition.router, prefix="/nutrition", tags=["nutrition"])

# Additional route modules (scaffolded folders, wire as built):
#   profiles, workouts, nutrition, progress, social, communities, feed,
#   recommendations, notifications, uploads  — see docs/10.
