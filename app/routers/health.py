"""
Health Check Router.

This module provides an endpoint to check the health status of the API.
"""
from fastapi import APIRouter
import os

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    """
    Perform a health check on the API.

    Returns:
        dict: A dictionary containing the current health status of the API.
    """
    return {"status": "healthy"}
