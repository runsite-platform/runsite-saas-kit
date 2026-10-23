from pydantic import BaseModel


class PublicFeatures(BaseModel):
    google_login: bool
    billing: bool
    file_uploads: bool
    email: bool


class PublicConfigResponse(BaseModel):
    brand_name: str
    features: PublicFeatures
