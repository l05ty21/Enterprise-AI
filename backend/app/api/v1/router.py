from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    approvals,
    attachments,
    auth,
    departments,
    health,
    knowledge,
    notifications,
    permissions,
    roles,
    tickets,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(departments.router)
api_router.include_router(ai.router)
api_router.include_router(knowledge.router)
api_router.include_router(tickets.router)
api_router.include_router(approvals.router)
api_router.include_router(attachments.router)
api_router.include_router(notifications.router)
