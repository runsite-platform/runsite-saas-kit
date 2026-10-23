from fastapi import APIRouter

from app.schemas.auth import StatusResponse
from app.schemas.users import ChangePasswordRequest, MeResponse, UpdateProfileRequest, UserResponse
from app.services.organization_service import OrganizationService
from app.services.user_service import UserService
from app.utils.dependencies import AccessClaims, CurrentUser, DbSession, OptionalObjectStorage

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
async def get_me(
    user: CurrentUser, claims: AccessClaims, session: DbSession, storage: OptionalObjectStorage
) -> MeResponse:
    user_response = await UserService(session).build_response(user, storage=storage)
    return MeResponse(
        user=user_response,
        organizations=await OrganizationService(session, storage=storage).list_summaries_for_user(user.id),
        impersonated_by=claims.impersonated_by,
    )


@router.patch("", response_model=UserResponse)
async def update_me(
    payload: UpdateProfileRequest, user: CurrentUser, session: DbSession, storage: OptionalObjectStorage
) -> UserResponse:
    user_service = UserService(session)
    await user_service.update_profile(user, full_name=payload.full_name)
    return await user_service.build_response(user, storage=storage)


@router.post("/password", response_model=StatusResponse)
async def change_password(payload: ChangePasswordRequest, user: CurrentUser, session: DbSession) -> StatusResponse:
    await UserService(session).change_password(
        user, current_password=payload.current_password, new_password=payload.new_password
    )
    return StatusResponse()
