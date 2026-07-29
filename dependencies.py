import database
from fastapi import HTTPException

def get_organization_or_404(
    organization_id: int,
) -> dict:
    organization = database.get_organization(
        organization_id
    )

    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    return organization

def get_task_or_404(organization_id:int, task_id: int) -> dict:
    task = database.get_task(organization_id, task_id)

    if task is None:
        raise HTTPException(
              status_code=404,
              detail="Task not found"
        )

    return task