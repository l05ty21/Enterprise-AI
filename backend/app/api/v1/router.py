from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import ai, auth, departments, health, permissions, roles, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(departments.router)
api_router.include_router(ai.router)
