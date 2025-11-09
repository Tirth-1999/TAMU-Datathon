"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

from app.routers import upload, classify, hitl

# Create FastAPI app
app = FastAPI(
    title="AI-Powered Regulatory Document Classifier",
    description="Classify documents into Public, Confidential, Highly Sensitive, or Unsafe categories",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(classify.router, prefix="/api/classify", tags=["classify"])
app.include_router(hitl.router, prefix="/api/hitl", tags=["hitl"])

# Create necessary directories
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Serve uploaded files (for development)
if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI-Powered Regulatory Document Classifier API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/upload/",
            "classify": "/api/classify/",
            "hitl": "/api/hitl/",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
