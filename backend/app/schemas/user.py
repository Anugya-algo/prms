"""
User Pydantic schemas.

Naming convention:
  UserBase        — shared fields
  UserCreate      — request body for POST /users (includes plain password)
  UserUpdate      — request body for PATCH /users/{id} (all fields optional)
  UserRead        — response body (no password; includes role)
  UserMe          — /auth/me response (same as UserRead)
  PasswordChange  — request body for PATCH /users/{id}/password
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.role import RoleRead


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    role_id: str | None = None


class UserCreate(UserBase):
    """Requires a plain-text password which will be hashed before persistence."""

    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """All fields optional to support partial updates."""

    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    role_id: str | None = None


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    role: RoleRead | None = None


# Alias — the /auth/me endpoint returns the same shape.
UserMe = UserRead
