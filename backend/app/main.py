"""
ReconET — Ethiopian Treasury Reconciliation Platform
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import reconciliation, cheques

app = FastAPI(
    title="ReconET API",
    description="Ethiopian treasury reconciliation platform — fee-aware matching",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reconciliation.router)
app.include_router(cheques.router)


@app.get("/")
async def root():
    return {
        "name": "ReconET API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "reconciliation": "/api/reconciliation/run",
            "cheques_stale": "/api/cheques/stale/{company_id}",
            "cheques_outstanding": "/api/cheques/outstanding/{company_id}",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
