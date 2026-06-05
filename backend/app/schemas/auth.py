"""Auth request/response schemas (docs/10 §2)."""
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str | None = Field(default=None, max_length=60)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UsernameAvailability(BaseModel):
    username: str
    available: bool
    reason: str | None = None  # why it's unavailable (taken / invalid), for the UI


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=10, pattern=r"^\d+$")
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    """Generic ack for endpoints that intentionally reveal nothing else."""

    message: str
