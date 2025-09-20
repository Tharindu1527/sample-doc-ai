# backend/middleware/auth_middleware.py
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth_service import auth_service
from models.user import UserRole, UserResponse
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

class AuthMiddleware:
    def __init__(self):
        self.auth_service = auth_service
    
    async def get_current_user_optional(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Get current user without raising error if not authenticated"""
        try:
            if not credentials:
                return None
            
            token = credentials.credentials
            user = await self.auth_service.get_current_user(token)
            return user
        except Exception as e:
            logger.warning(f"Optional auth failed: {e}")
            return None
    
    async def require_auth(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Require authentication"""
        if not credentials:
            logger.error("No credentials provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required - no credentials provided",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            token = credentials.credentials
            user = await self.auth_service.get_current_user(token)
            if not user:
                logger.error("Invalid token - user not found")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user.is_active:
                logger.error(f"User {user.email} is not active")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is deactivated"
                )
            
            logger.info(f"Authentication successful for user: {user.email} (role: {user.role})")
            return user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def require_role(self, allowed_roles: list[UserRole], credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Require specific role"""
        user = await self.require_auth(credentials)
        
        if user.role not in allowed_roles:
            logger.error(f"User {user.email} with role {user.role} attempted to access endpoint requiring {allowed_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in allowed_roles]}, your role: {user.role.value}"
            )
        
        return user
    
    async def require_doctor(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Require doctor role"""
        return await self.require_role([UserRole.DOCTOR, UserRole.ADMIN], credentials)
    
    async def require_patient(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Require patient role"""
        return await self.require_role([UserRole.PATIENT, UserRole.ADMIN], credentials)
    
    async def require_admin(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Require admin role"""
        return await self.require_role([UserRole.ADMIN], credentials)
    
    async def require_doctor_or_patient(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Require doctor or patient role"""
        return await self.require_role([UserRole.DOCTOR, UserRole.PATIENT, UserRole.ADMIN], credentials)

# Global middleware instance
auth_middleware = AuthMiddleware()

# Helper functions for route protection
async def get_current_user_from_token(token: str):
    """Get user from token string"""
    return await auth_service.get_current_user(token)

def check_appointment_access(user: UserResponse, appointment) -> bool:
    """Check if user can access specific appointment"""
    if user.role == UserRole.ADMIN:
        return True
    elif user.role == UserRole.DOCTOR:
        # Doctor can only see their own appointments
        expected_doctor_name = f"Dr. {user.first_name} {user.last_name}"
        return appointment.doctor_name == expected_doctor_name
    elif user.role == UserRole.PATIENT:
        # Patient can only see their own appointments
        return appointment.patient_id == user.patient_id
    return False

def check_patient_access(user: UserResponse, patient) -> bool:
    """Check if user can access specific patient"""
    if user.role == UserRole.ADMIN:
        return True
    elif user.role == UserRole.PATIENT:
        # Patient can only access their own record
        return patient.patient_id == user.patient_id
    elif user.role == UserRole.DOCTOR:
        # Doctors can access patients they have appointments with
        return True  # For now, allow doctors to see all patients
    return False

def check_doctor_access(user: UserResponse, doctor) -> bool:
    """Check if user can access specific doctor"""
    if user.role == UserRole.ADMIN:
        return True
    elif user.role == UserRole.DOCTOR:
        # Doctor can only access their own record
        return doctor.doctor_id == user.doctor_id
    elif user.role == UserRole.PATIENT:
        # Patients can view doctor profiles
        return True
    return False