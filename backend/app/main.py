"""
Retail Demand Prediction System - FastAPI Application
A decision engine for kirana stores to know what to reorder, how much, and when.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes
from app.config.settings import settings

app = FastAPI(
    title="Retail Demand Prediction System",
    description="Help kirana stores know what to reorder, how much, and when",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Retail Demand Prediction System API",
        "docs": "/docs",
        "health": "ok"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
