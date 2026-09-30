from fastapi import FastAPI
from app.database import engine

from app.models.customer import Customer

app = FastAPI(title="AI Support Orchestration")


@app.get("/")
def root():
    return {"message": " Ecommerece AI Support Orchestration API is running"}



@app.get("/db-test")
def database_test():
    with engine.connect():
        return {"database": "connected"}