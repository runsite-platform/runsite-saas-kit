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

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(public_config.router, prefix="/config", tags=["Config"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(notifications.router, prefix="/me/notifications", tags=["Notifications"])
api_router.include_router(me.router, prefix="/me", tags=["Me"])
api_router.include_router(organizations.router, prefix="/orgs", tags=["Organizations"])
api_router.include_router(members.router, prefix="/orgs/{org_id}/members", tags=["Members"])
api_router.include_router(
    invitations.organization_invitations_router, prefix="/orgs/{org_id}/invitations", tags=["Invitations"]
)
api_router.include_router(invitations.public_invitations_router, prefix="/invitations", tags=["Invitations"])
api_router.include_router(projects.router, prefix="/orgs/{org_id}/projects", tags=["Projects"])
api_router.include_router(files.router, prefix="/orgs/{org_id}/files", tags=["Files"])
api_router.include_router(media.router, tags=["Media"])
api_router.include_router(billing.router, tags=["Billing"])
api_router.include_router(overview.router, prefix="/orgs/{org_id}/overview", tags=["Overview"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["Admin"])
api_router.include_router(admin_organizations.router, prefix="/admin/organizations", tags=["Admin"])
api_router.include_router(admin_platform.router, prefix="/admin", tags=["Admin"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
