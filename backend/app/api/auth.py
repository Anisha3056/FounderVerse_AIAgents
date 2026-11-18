import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from app.config.settings import get_settings
from app.database.models.user import (
    EmailVerificationRequest,
    UserLogin,
    UserRegister,
)
from app.database.repositories.user_repository import UserRepository
from app.email_service import send_verification_email


logger = logging.getLogger(__name__)

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


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _check_email_domain(email: str) -> str:
    """Validate address syntax and check that its domain is mail-routable.

    DNS deliverability does not prove that an individual mailbox exists.
    The one-time confirmation link proves that the user can access it.
    """
    try:
        result = await asyncio.to_thread(
            validate_email,
            email,
            check_deliverability=True,
        )
        return result.normalized.lower()
    except EmailNotValidError as exc:
        raise HTTPException(
            status_code=422,
            detail="This email address or its domain cannot receive email. Check the address and try again.",
        ) from exc
    except Exception as exc:
        logger.exception("Email-domain deliverability check failed")
        raise HTTPException(
            status_code=503,
            detail="We couldn't check this email domain right now. Please try again.",
        ) from exc


async def _issue_verification_email(email: str) -> bool:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.email_verification_expiry_minutes
    )
    now = datetime.now(timezone.utc)

    stored = repository.set_email_verification(
        email=email,
        token_hash=_token_hash(raw_token),
        expires_at=expires_at,
        sent_at=now,
        cooldown_seconds=settings.email_verification_resend_cooldown_seconds,
    )

    if not stored:
        return False

    try:
        await asyncio.to_thread(send_verification_email, email, raw_token)
    except Exception:
        repository.clear_email_verification_attempt(email)
        raise

    return True


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

    if not user.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "message": "Please verify your email address before accessing FounderVerse.",
            },
        )

    return user


@router.post("/register", status_code=202)
async def register(user: UserRegister):
    email = await _check_email_domain(str(user.email))

    existing_user = repository.get_by_email(email)

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Try logging in or resending the verification email.",
        )

    hashed_password = password_hash.hash(user.password)

    user_id = repository.create(
        email=email,
        password_hash=hashed_password,
    )

    try:
        await _issue_verification_email(email)
    except Exception as exc:
        logger.exception("Failed to send verification email for new account")
        raise HTTPException(
            status_code=503,
            detail="Your account was created but the verification email could not be sent. Please use Resend verification after the email service is available.",
        ) from exc

    return {
        "user_id": user_id,
        "email": email,
        "message": "Account created. Check your inbox for the verification link before logging in.",
    }


@router.get("/verify-email")
async def verify_email(token: str):
    if not token or len(token) > 200:
        raise HTTPException(
            status_code=400,
            detail="This verification link is invalid or has expired.",
        )

    user = repository.verify_email_token(
        token_hash=_token_hash(token),
        verified_at=datetime.now(timezone.utc),
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="This verification link is invalid, already used, or has expired. Request a new link and try again.",
        )

    return {
        "message": "Email verified successfully. You can now log in to FounderVerse.",
    }


@router.post("/resend-verification")
async def resend_verification(request: EmailVerificationRequest):
    email = str(request.email).strip().lower()
    existing_user = repository.get_by_email(email)

    # Use the same response for unknown, already-verified, and pending
    # accounts so this endpoint does not disclose account existence.
    if existing_user and not existing_user.get("email_verified", False):
        try:
            await _issue_verification_email(email)
        except Exception:
            logger.exception("Failed to resend verification email")

    return {
        "message": "If an unverified FounderVerse account exists for this address, a verification email has been sent. Check your inbox and spam folder.",
    }


@router.post("/login")
async def login(user: UserLogin):
    existing_user = repository.get_by_email(str(user.email))

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

    if not existing_user.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "message": "Please verify your email address before logging in. You can request a new verification link below.",
            },
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
        "email_verified": current_user.get("email_verified", False),
    }
