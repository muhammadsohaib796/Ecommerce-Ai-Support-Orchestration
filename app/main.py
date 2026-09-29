from fastapi import FastAPI

app = FastAPI(title="AI Support Orchestration")


@app.get("/")
def root():
    return {"message": " Ecommerece AI Support Orchestration API is running"}