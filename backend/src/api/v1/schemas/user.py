from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

RoleType = Literal["admin", "user"]


class GroupInfo(BaseModel):
    id: int
    name: str


class UserListItemResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: str | None
    groups: list[GroupInfo] = []


class CreateUserRequest(BaseModel):
    email: EmailStr
    display_name: str
    role: RoleType


class CreateUserResponse(BaseModel):
    id: int
    invite_token: str


class UpdateUserRequest(BaseModel):
    display_name: str
    role: RoleType


class UserStatusRequest(BaseModel):
    is_active: bool


class InviteValidateResponse(BaseModel):
    email: str


class InviteAcceptRequest(BaseModel):
    password: str = Field(min_length=8)


class RegenerateInviteResponse(BaseModel):
    invite_token: str
