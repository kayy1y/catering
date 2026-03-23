from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine, get_db
from app.api import router as api_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Plataforma de Catering", version="1.0.0")
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Plataforma de catering operativa", "frontend": "/web", "api_docs": "/docs"}


if frontend_dir.exists():
    app.mount("/web", StaticFiles(directory=frontend_dir, html=True), name="frontend")
