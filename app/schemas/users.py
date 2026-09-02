from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    is_admin: bool = False


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    api_access_enabled: bool
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None


class ApiTokenIssued(BaseModel):
    user: UserPublic
    token: str
