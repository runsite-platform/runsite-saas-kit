from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.stored_file_repository import StoredFileRepository
from app.services.billing.plans import Plan, get_plan
from app.utils.exceptions import BusinessError
from app.utils.security import utc_now

BYTES_PER_MEGABYTE = 1024 * 1024


def plan_limit_reached(limit_name: str, plan: Plan) -> BusinessError:
    """Return the error for a reached plan limit."""
    return BusinessError(
        "plan_limit_reached",
        f"The {plan.name} plan limit for {limit_name} is reached. Upgrade the plan to add more.",
        status_code=402,
        details={"limit": limit_name, "plan_id": plan.id},
    )


class PlanLimitsService:
    """Service that enforces organization plan limits."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.membership_repository = MembershipRepository(db)
        self.invitation_repository = InvitationRepository(db)

    async def ensure_can_add_member(self, organization: Organization) -> None:
        """Raise if members plus pending invitations reach the plan limit."""
        plan = get_plan(organization.plan_id)
        member_count = await self.membership_repository.count_for_organization(organization.id)
        pending_invitation_count = await self.invitation_repository.count_pending_for_organization(
            organization.id, utc_now()
        )
        if member_count + pending_invitation_count >= plan.limits.members:
            raise plan_limit_reached("members", plan)

    async def ensure_can_add_project(self, organization: Organization) -> None:
        """Raise if the organization reached its project limit."""
        plan = get_plan(organization.plan_id)
        project_count = await ProjectRepository(self.db).count_for_organization(organization.id)
        if project_count >= plan.limits.projects:
            raise plan_limit_reached("projects", plan)

    async def ensure_can_store(self, organization: Organization, extra_bytes: int) -> None:
        """Raise if storing extra bytes would exceed the storage limit."""
        plan = get_plan(organization.plan_id)
        used_bytes = await StoredFileRepository(self.db).total_size_for_organization(organization.id)
        if used_bytes + extra_bytes > plan.limits.storage_mb * BYTES_PER_MEGABYTE:
            raise plan_limit_reached("storage_mb", plan)
