from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from app.models.membership import Membership
from app.services.file_storage import ObjectStorage, presigned_url_or_none
from app.utils.slugs import SLUG_MAX_LENGTH, SLUG_PATTERN

OrganizationName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
OrganizationSlug = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=SLUG_MAX_LENGTH, pattern=SLUG_PATTERN)
]


class OrganizationCreateRequest(BaseModel):
    name: OrganizationName


class OrganizationUpdateRequest(BaseModel):
    name: OrganizationName | None = None
    slug: OrganizationSlug | None = None


class TransferOwnershipRequest(BaseModel):
    membership_id: UUID


class OrganizationSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str
    plan_id: str
    logo_url: str | None = None

    @classmethod
    def from_membership(cls, membership: Membership, *, storage: ObjectStorage | None = None) -> Self:
        """`membership.organization` must be loaded."""
        organization = membership.organization
        return cls(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            role=membership.role,
            plan_id=organization.plan_id,
            logo_url=presigned_url_or_none(storage, organization.logo_key),
        )


class PlanLimitsResponse(BaseModel):
    members: int
    projects: int
    storage_mb: int


class OrganizationDetailResponse(OrganizationSummary):
    plan_name: str
    owner_id: UUID | None
    member_count: int
    pending_invitation_count: int
    limits: PlanLimitsResponse
    created_at: datetime
