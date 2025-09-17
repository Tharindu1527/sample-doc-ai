# backend/models/user.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"
    STAFF = "staff"

class User(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    password_hash: str = Field(..., description="Hashed password")
    role: UserRole = Field(..., description="User role")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(default=True, description="Account status")
    is_verified: bool = Field(default=False, description="Email verification status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Role-specific IDs
    doctor_id: Optional[str] = Field(None, description="Reference to doctor record")
    patient_id: Optional[str] = Field(None, description="Reference to patient record")
    
    # Profile information
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    department: Optional[str] = Field(None, description="Department (for doctors/staff)")
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    role: UserRole = Field(..., description="User role")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    department: Optional[str] = Field(None, description="Department")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, description="User email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    department: Optional[str] = Field(None, description="Department")
    is_active: Optional[bool] = Field(None, description="Account status")

class UserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    role: UserRole = Field(..., description="User role")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(..., description="Account status")
    is_verified: bool = Field(..., description="Email verification status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    doctor_id: Optional[str] = Field(None, description="Reference to doctor record")
    patient_id: Optional[str] = Field(None, description="Reference to patient record")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    department: Optional[str] = Field(None, description="Department")

    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(default=False, description="Remember login")

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserResponse = Field(..., description="User information")

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")

class PasswordReset(BaseModel):
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")

class ChangePassword(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")