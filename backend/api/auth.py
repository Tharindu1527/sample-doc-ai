# backend/api/auth.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user import (
    UserCreate, UserResponse, LoginRequest, LoginResponse, 
    TokenResponse, PasswordResetRequest, PasswordReset, ChangePassword, UserRole
)
from services.auth_service import auth_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """Get current authenticated user"""
    user = await auth_service.get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Role-based access control
def require_role(allowed_roles: list[UserRole]):
    """Decorator to require specific roles"""
    def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

# Public routes
@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        user = await auth_service.register_user(user_data)
        logger.info(f"New user registered: {user.email}")
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Authenticate user and return tokens"""
    try:
        user = await auth_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        tokens = await auth_service.create_tokens(user)
        
        logger.info(f"User logged in: {user.email}")
        
        return LoginResponse(
            **tokens,
            user=user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token"""
    try:
        tokens = await auth_service.refresh_token(refresh_token)
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return TokenResponse(
            access_token=tokens["access_token"],
            token_type=tokens["token_type"]
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")

# Protected routes
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: UserResponse = Depends(get_current_user)
):
    """Change user password"""
    try:
        success = await auth_service.change_password(
            current_user.user_id,
            password_data.current_password,
            password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        return {"message": "Password changed successfully"}
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(status_code=500, detail="Password change failed")

@router.post("/logout")
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """Logout user (client should discard tokens)"""
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Logged out successfully"}

# Admin routes
@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN]))
):
    """Get all users (admin only)"""
    try:
        # This would need to be implemented in auth_service
        # For now, return empty list
        return []
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")

# Role verification endpoints
@router.get("/verify-doctor")
async def verify_doctor_access(
    current_user: UserResponse = Depends(require_role([UserRole.DOCTOR, UserRole.ADMIN]))
):
    """Verify doctor access"""
    return {"message": "Doctor access verified", "user": current_user}

@router.get("/verify-patient")
async def verify_patient_access(
    current_user: UserResponse = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    """Verify patient access"""
    return {"message": "Patient access verified", "user": current_user}

@router.get("/verify-admin")
async def verify_admin_access(
    current_user: UserResponse = Depends(require_role([UserRole.ADMIN]))
):
    """Verify admin access"""
    return {"message": "Admin access verified", "user": current_user}