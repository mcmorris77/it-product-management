from fastapi import FastAPI
from .database import create_tables

create_tables()

app = FastAPI(title="Split Bill")

@app.get("/health")
def health():
    return {"status": "ok"}