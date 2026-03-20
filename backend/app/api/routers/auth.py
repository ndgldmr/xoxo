"""Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import LoginRequest, TokenResponse
from app.config import get_settings
from app.repositories.admin import AdminRepository
from app.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS = HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate an admin and return a JWT access token."""
    repo = AdminRepository(db)
    admin = repo.get_by_email(body.email)
    if not admin or not verify_password(body.password, admin.hashed_password):
        raise _INVALID_CREDENTIALS

    settings = get_settings()
    token = create_access_token(
        email=admin.email,
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_hours=settings.jwt_expire_hours,
    )
    return TokenResponse(access_token=token)
