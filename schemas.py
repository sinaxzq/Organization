from typing import Literal
from pydantic import BaseModel, Field

TaskStatus = Literal["todo", "in_progress", "done"]

class TaskCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )
    status: TaskStatus = "todo"

class TaskUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    status: TaskStatus | None = None

class TaskResponse(BaseModel):
    id: int
    title: str
    status: TaskStatus

class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    count: int
    total: int
    limit: int
    offset: int

class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

class OrganizationResponse(BaseModel):
    id: int
    name: str