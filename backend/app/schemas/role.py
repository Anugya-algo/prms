"""
Role Pydantic schemas.

Naming convention:
  RoleBase        — shared fields (used in both Create and Update)
  RoleCreate      — request body for POST /roles
  RoleUpdate      — request body for PATCH /roles/{id}
  RoleRead        — response body (includes id, timestamps)
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["admin"])
    description: str | None = Field(None, max_length=500)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    """All fields optional — supports partial updates."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class RoleRead(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
