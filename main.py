from fastapi import FastAPI
from contextlib import asynccontextmanager

import database

from routers import organizations, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_database()

    yield


app = FastAPI(lifespan=lifespan)

app.include_router(organizations.router)
app.include_router(tasks.router)


@app.get("/")
def root():
    return {"message": "Operations Platform API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
