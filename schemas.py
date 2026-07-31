from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

TaskStatus = Literal["todo", "in_progress", "done"]

class TaskCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )
    status: TaskStatus = "todo"

    @field_validator(
        "title",
    )
    @classmethod
    def reject_dull(
        cls,
        value: str
    ) -> str:
        return normalize_task_title(value)

        

class TaskUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    status: TaskStatus | None = None

    @field_validator(
        "title",
        "status",
        mode="before",
    )
    def reject_null(
        value: Any,
    ) -> Any:
        if value is None:
            raise ValueError(
                "Field cannot be null"
            )

        return value

    @field_validator("title")
    def validate_title(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return normalize_task_title(value)

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

def normalize_task_title(value: str) -> str:
    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(
            "Title cannot be blank"
        )

    return normalized_value