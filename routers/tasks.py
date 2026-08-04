from fastapi import APIRouter, Depends, Query, HTTPException

import database

from dependencies import (
    get_organization_or_404,
    get_task_or_404,
)
from schemas import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
    TaskSort,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/tasks",
    tags=["tasks"],
    dependencies=[
        Depends(get_organization_or_404),
    ],
)


@router.get("", response_model=TaskListResponse)
def get_tasks(
    organization_id: int,
    status: TaskStatus | None = None,
    q: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    priority: int | None = Query(
        default=None,
        ge=0,
        le=5,
    ),
    assignee_id: int | None = Query(
        default=None,
        ge=1,
    ),
    sort: TaskSort = "id",
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):

    page_tasks, total = database.get_tasks(
        organization_id=organization_id,
        status=status,
        q=q,
        priority=priority,
        assignee_id=assignee_id,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    return {
        "items": page_tasks,
        "count": len(page_tasks),
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    organization_id: int,
    task_id: int,
):
    return get_task_or_404(
        organization_id=organization_id,
        task_id=task_id,
    )


@router.post(
    "",
    status_code=201,
    response_model=TaskResponse,
)
def create_task(organization_id: int, task: TaskCreate):
    validate_assignee(
        organization_id=organization_id,
        assignee_id=task.assignee_id,
    )

    return database.create_task(
        organization_id=organization_id,
        title=task.title,
        status=task.status,
        priority=task.priority,
        due_date=(task.due_date.isoformat() if task.due_date is not None else None),
        assignee_id=task.assignee_id,
    )


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(organization_id: int, task_id: int, update: TaskUpdate):
    update_data = update.model_dump(
        exclude_unset=True,
        mode="json",
    )

    if "assignee_id" in update_data:
        validate_assignee(
            organization_id=organization_id,
            assignee_id=update_data["assignee_id"],
        )

    updated_task = database.update_task(
        organization_id=organization_id,
        task_id=task_id,
        update_data=update_data,
    )

    if updated_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return updated_task


@router.delete("/{task_id}", status_code=204)
def delete_task(organization_id: int, task_id: int):
    deleted = database.delete_task(organization_id, task_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )


def validate_assignee(
    organization_id: int,
    assignee_id: int | None,
) -> None:
    if assignee_id is None:
        return

    member = database.get_member(
        organization_id=organization_id,
        member_id=assignee_id,
    )

    if member is None:
        raise HTTPException(
            status_code=422,
            detail=("Assignee does not belong to this organization"),
        )
