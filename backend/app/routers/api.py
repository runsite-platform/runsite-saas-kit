from fastapi import APIRouter

from app.routers.routes import (
    admin_organizations,
    admin_platform,
    admin_users,
    auth,
    billing,
    files,
    health,
    invitations,
    me,
    media,
    members,
    notifications,
    organizations,
    overview,
    projects,
    public_config,
    webhooks,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(public_config.router)
api_router.include_router(auth.router)
api_router.include_router(notifications.router)
api_router.include_router(me.router)
api_router.include_router(organizations.router)
api_router.include_router(members.router)
api_router.include_router(invitations.organization_invitations_router)
api_router.include_router(invitations.public_invitations_router)
api_router.include_router(projects.router)
api_router.include_router(files.router)
api_router.include_router(media.router)
api_router.include_router(billing.router)
api_router.include_router(overview.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_organizations.router)
api_router.include_router(admin_platform.router)
api_router.include_router(webhooks.router)
