from pydantic import BaseModel


class AvatarResponse(BaseModel):
    avatar_url: str | None


class LogoResponse(BaseModel):
    logo_url: str | None
