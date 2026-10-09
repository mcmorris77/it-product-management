from fastapi import FastAPI
from .database import create_tables
from .routers import checks

create_tables()

app = FastAPI(title="Split Bill")
app.include_router(checks.router)

@app.get("/health")
def health():
    return {"status": "ok"}