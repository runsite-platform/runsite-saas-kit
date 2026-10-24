from fastapi import APIRouter

from app.schemas.auth import StatusResponse
from app.schemas.users import ChangePasswordRequest, MeResponse, UpdateProfileRequest, UserResponse
from app.services.organization_service import OrganizationService
from app.services.user_service import UserService
from app.utils.dependencies import AccessClaims, CurrentUser, DbSession, OptionalObjectStorage

router = APIRouter()


@router.get("", response_model=MeResponse)
async def get_me(user: CurrentUser, claims: AccessClaims, db: DbSession, storage: OptionalObjectStorage) -> MeResponse:
    """Return the current user with organizations."""
    user_response = await UserService(db).build_response(user, storage=storage)
    return MeResponse(
        user=user_response,
        organizations=await OrganizationService(db, storage=storage).list_summaries_for_user(user.id),
        impersonated_by=claims.impersonated_by,
    )


@router.patch("", response_model=UserResponse)
async def update_me(
    payload: UpdateProfileRequest, user: CurrentUser, db: DbSession, storage: OptionalObjectStorage
) -> UserResponse:
    """Update the current user profile."""
    user_service = UserService(db)
    await user_service.update_profile(user, full_name=payload.full_name)
    return await user_service.build_response(user, storage=storage)


@router.post("/password", response_model=StatusResponse)
async def change_password(payload: ChangePasswordRequest, user: CurrentUser, db: DbSession) -> StatusResponse:
    """Change the current user password."""
    await UserService(db).change_password(
        user, current_password=payload.current_password, new_password=payload.new_password
    )
    return StatusResponse()
