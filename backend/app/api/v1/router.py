"""
API v1 router aggregating all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, students, users

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])

# Add more routers here as they are created
# api_router.include_router(volunteers.router, prefix="/volunteers", tags=["Volunteers"])
# api_router.include_router(programs.router, prefix="/programs", tags=["Programs"])
