from fastapi import HTTPException, FastAPI, Query, Depends
from pydantic import BaseModel, Field
from typing import Literal
from contextlib import asynccontextmanager
import database
import sqlite3

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_database()

    yield

app = FastAPI(lifespan=lifespan)
            
@app.get("/")
def root():
    return {"message": "Operations Platform API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

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

TaskStatus = Literal["todo", "in_progress", "done"]

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

@app.get("/organizations/{organization_id}/tasks", response_model=TaskListResponse, dependencies=[
        Depends(get_organization_or_404)
    ],)
def get_tasks(organization_id: int,
              status: TaskStatus | None = None,
              limit: int = Query(default=10, ge=1, le=100),
              offset: int = Query(default=0, ge=0),
              q: str | None = Query(
                  default=None,
                  min_length=1,
                  max_length=100,
              )
              ):

    page_tasks, total = database.get_tasks(
    organization_id=organization_id,
    status=status,
    q=q,
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

@app.get(
    "/organizations/{organization_id}/tasks/{task_id}",
    response_model=TaskResponse,
     dependencies=[
        Depends(get_organization_or_404)
    ],
)
def get_task(
    organization_id: int,
    task_id: int,
):
    return get_task_or_404(
        organization_id=organization_id,
        task_id=task_id,
    )
    
@app.post("/organizations/{organization_id}/tasks", status_code=201, response_model=TaskResponse, dependencies=[
        Depends(get_organization_or_404)
    ],)
def create_task(organization_id:int, task:TaskCreate):
    return database.create_task(
    organization_id = organization_id,
    title=task.title,
    status=task.status,
    )

@app.patch("/organizations/{organization_id}/tasks/{task_id}", response_model=TaskResponse, dependencies=[
        Depends(get_organization_or_404)
    ],)
def update_task(organization_id: int, task_id: int, update: TaskUpdate):
    update_data = update.model_dump(exclude_unset=True)

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

@app.delete("/organizations/{organization_id}/tasks/{task_id}", status_code=204, dependencies=[
        Depends(get_organization_or_404)
    ],)
def delete_task(organization_id: int, task_id: int):
    deleted = database.delete_task(organization_id, task_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

class OrganizationResponse(BaseModel):
    id: int
    name: str

@app.get(
    "/organizations",
    response_model=list[OrganizationResponse],
    
)
def get_organizations():
    return database.get_organizations()


@app.post(
    "/organizations",
    status_code=201,
    response_model=OrganizationResponse,
)
def create_organization(organization: OrganizationCreate):
    created_organization = database.create_organization(
        organization.name
    )

    if created_organization is None:
        raise HTTPException(
            status_code=409,
            detail="Organization name already exists",
        )

    return created_organization

@app.get(
    "/organizations/{organization_id}",
    response_model=OrganizationResponse,
)
def get_organization(
    organization_id: int,
):
    return get_organization_or_404(
        organization_id
    )