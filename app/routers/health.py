from fastapi import APIRouter
import os
router = APIRouter()

@router.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy"}
