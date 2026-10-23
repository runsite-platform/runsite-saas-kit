from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.repositories.invitation_repository import InvitationRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.stored_file_repository import StoredFileRepository
from app.utils.repository import SQLAlchemyRepository


@dataclass(frozen=True)
class OrganizationUsage:
    members: int
    pending_invitations: int
    projects: int
    storage_bytes: int


class UsageRepository(SQLAlchemyRepository):
    """Reads the same counters PlanLimitsService checks, so the Billing page matches the limit errors."""

    async def get_usage(self, organization_id: UUID) -> OrganizationUsage:
        members = await MembershipRepository(self.db).count_for_organization(organization_id)
        pending_invitations = await InvitationRepository(self.db).count_pending_for_organization(
            organization_id, datetime.now(UTC)
        )
        projects = await ProjectRepository(self.db).count_for_organization(organization_id)
        storage_bytes = await StoredFileRepository(self.db).total_size_for_organization(organization_id)
        return OrganizationUsage(
            members=members,
            pending_invitations=pending_invitations,
            projects=projects,
            storage_bytes=storage_bytes,
        )
