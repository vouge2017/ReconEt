"""
ReconET — Ethiopian Treasury Reconciliation Platform
Main FastAPI application
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import reconciliation, cheques
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.periods import router as periods_router
from app.api.gl_mappings import router as gl_mappings_router
from app.api.cash import router as cash_router
from app.api.fees import router as fees_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ReconET API",
    description="Ethiopian treasury reconciliation platform — fee-aware matching",
    version="1.0.0"
)

# CORS for frontend — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(reconciliation.router)
app.include_router(cheques.router)
app.include_router(dashboard_router)
app.include_router(periods_router)
app.include_router(gl_mappings_router)
app.include_router(cash_router)
app.include_router(fees_router)


@app.on_event("startup")
async def startup_event():
    logger.info("ReconET API starting...")


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
