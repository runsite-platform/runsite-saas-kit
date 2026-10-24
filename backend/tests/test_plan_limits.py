from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import OrgRole
from app.services.plan_limits import PlanLimitsService
from app.utils.exceptions import BusinessError
from tests.factories import add_member, create_invitation, create_organization, create_user


async def test_allows_member_below_limit(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=await create_user(db_session))

    await PlanLimitsService(db_session).ensure_can_add_member(organization)


async def test_pending_invitations_count_against_member_limit(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=await create_user(db_session))
    await create_invitation(db_session, organization=organization, invited_by=owner, email="pending@example.com")

    with pytest.raises(BusinessError) as error_info:
        await PlanLimitsService(db_session).ensure_can_add_member(organization)

    assert error_info.value.code == "plan_limit_reached"
    assert error_info.value.status_code == 402
    assert error_info.value.details == {"limit": "members", "plan_id": "free"}


async def test_expired_and_accepted_invitations_do_not_count(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    await add_member(db_session, organization=organization, user=await create_user(db_session))
    await create_invitation(
        db_session, organization=organization, invited_by=owner, email="old@example.com", expires_in=timedelta(days=-1)
    )
    await create_invitation(
        db_session, organization=organization, invited_by=owner, email="done@example.com", accepted=True
    )

    await PlanLimitsService(db_session).ensure_can_add_member(organization)


async def test_pro_plan_has_higher_member_limit(db_session: AsyncSession) -> None:
    owner = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, plan_id="pro")
    for _index in range(3):
        await add_member(db_session, organization=organization, user=await create_user(db_session), role=OrgRole.ADMIN)

    await PlanLimitsService(db_session).ensure_can_add_member(organization)
