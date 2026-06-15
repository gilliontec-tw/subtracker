from pydantic import BaseModel, Field


class GroupBasicResponse(BaseModel):
    id: int
    name: str


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GroupMemberAdd(BaseModel):
    user_id: int


class GroupMemberResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
