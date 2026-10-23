from fastapi import FastAPI
from .database import create_tables
from .routers import checks, claims
from pathlib import Path
from fastapi.responses import FileResponse

create_tables()

app = FastAPI(title="Split Bill")
app.include_router(checks.router)
app.include_router(claims.router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/app")
def mini_app():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
