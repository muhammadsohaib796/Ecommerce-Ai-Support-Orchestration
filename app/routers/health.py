from fastapi import APIRouter

from app.database import engine

router = APIRouter(tags=["health"])


@router.get("/")
def root():
    return {"message": "AI Support Orchestration API is running"}


@router.get("/db-test")
def database_test():
    with engine.connect():
        return {"database": "connected"}