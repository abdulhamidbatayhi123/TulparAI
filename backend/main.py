"""TulparAI FastAPI entry point.

Run with:
    cd backend
    ./.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap DB schema on first start (idempotent)
    init_db()

    # Load anomaly detection model
    from backend.anomaly.router import load_anomaly_model
    load_anomaly_model()

    yield


app = FastAPI(
    title="TulparAI Backend",
    description="Verified, multi-agent, tool-using AI adviser for Turkish athletes",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
from backend.api.chat import router as chat_router
from backend.api.profile import router as profile_router
from backend.api.logs import router as logs_router
from backend.api.upload import router as upload_router
app.include_router(chat_router)
app.include_router(profile_router)
app.include_router(logs_router)
app.include_router(upload_router)

# Mount anomaly detection router
from backend.anomaly.router import router as anomaly_router
app.include_router(anomaly_router)

# Serve anomaly dashboard static assets
from fastapi.staticfiles import StaticFiles
_anomaly_dashboard_dir = os.path.join(
    os.path.dirname(__file__), "anomaly", "dashboard"
)
if os.path.isdir(_anomaly_dashboard_dir):
    app.mount(
        "/anomaly-dashboard",
        StaticFiles(directory=_anomaly_dashboard_dir, html=True),
        name="anomaly-dashboard",
    )


@app.get("/health")
def health():
    """Liveness probe. Used by Brev healthchecks and the pre-submission checklist."""
    return {
        "status": "ok",
        "service": "tulparai-backend",
        "version": "0.1.0",
        "models": {
            "reasoner": settings.nemotron_reasoner,
            "fast": settings.nemotron_fast,
            "embed": settings.embedding_model,
        },
    }


@app.get("/")
def root():
    return {
        "service": "tulparai",
        "message": "🐎 Tulpar — Türk sporcular için doğrulanmış AI antrenör",
        "docs": "/docs",
        "health": "/health",
    }
