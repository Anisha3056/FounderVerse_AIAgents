from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from app.config.settings import get_settings
from app.database.models.user import UserLogin, UserRegister
from app.database.repositories.user_repository import UserRepository


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

repository = UserRepository()
security = HTTPBearer()
password_hash = PasswordHash.recommended()


def create_access_token(user_id: str) -> str:

    settings = get_settings()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": user_id,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):

    settings = get_settings()

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token.",
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired.",
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
        )

    user = repository.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found.",
        )

    return user


@router.post("/register")
async def register(user: UserRegister):

    existing_user = repository.get_by_email(user.email)

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    hashed_password = password_hash.hash(user.password)

    user_id = repository.create(
        email=user.email,
        password_hash=hashed_password,
    )

    token = create_access_token(user_id)

    return {
        "user_id": user_id,
        "access_token": token,
        "token_type": "bearer",
        "company_id": None,
        "message": "Account created successfully.",
    }


@router.post("/login")
async def login(user: UserLogin):

    existing_user = repository.get_by_email(user.email)

    if not existing_user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if not password_hash.verify(
        user.password,
        existing_user["password_hash"],
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    user_id = str(existing_user["_id"])

    token = create_access_token(user_id)

    return {
        "user_id": user_id,
        "access_token": token,
        "token_type": "bearer",
        "company_id": existing_user.get("company_id"),
        "message": "Login successful.",
    }


@router.get("/me")
async def me(current_user=Depends(get_current_user)):

    return {
        "user_id": str(current_user["_id"]),
        "email": current_user["email"],
        "company_id": current_user.get("company_id"),
    }