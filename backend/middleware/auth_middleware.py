# backend/middleware/auth_middleware.py
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.requests import Request
from services.auth_service import auth_service
from models.user import UserRole
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

class AuthMiddleware:
    def __init__(self):
        self.auth_service = auth_service
    
    async def get_current_user_optional(self, request: Request):
        """Get current user without raising error if not authenticated"""
        try:
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None
            
            token = authorization.replace("Bearer ", "")
            user = await self.auth_service.get_current_user(token)
            return user
        except Exception as e:
            logger.warning(f"Optional auth failed: {e}")
            return None
    
    async def require_auth(self, request: Request):
        """Require authentication"""
        user = await self.get_current_user_optional(request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    
    async def require_role(self, request: Request, allowed_roles: list[UserRole]):
        """Require specific role"""
        user = await self.require_auth(request)
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    
    async def require_doctor(self, request: Request):
        """Require doctor role"""
        return await self.require_role(request, [UserRole.DOCTOR, UserRole.ADMIN])
    
    async def require_patient(self, request: Request):
        """Require patient role"""
        return await self.require_role(request, [UserRole.PATIENT, UserRole.ADMIN])
    
    async def require_admin(self, request: Request):
        """Require admin role"""
        return await self.require_role(request, [UserRole.ADMIN])
    
    async def require_doctor_or_patient(self, request: Request):
        """Require doctor or patient role"""
        return await self.require_role(request, [UserRole.DOCTOR, UserRole.PATIENT, UserRole.ADMIN])

# Global middleware instance
auth_middleware = AuthMiddleware()

# Helper functions for route protection
async def get_current_user_from_token(token: str):
    """Get user from token string"""
    return await auth_service.get_current_user(token)

def check_appointment_access(user, appointment):
    """Check if user can access specific appointment"""
    if user.role == UserRole.ADMIN:
        return True
    elif user.role == UserRole.DOCTOR:
        # Doctor can only see their own appointments
        return appointment.doctor_name == f"Dr. {user.first_name} {user.last_name}"
    elif user.role == UserRole.PATIENT:
        # Patient can only see their own appointments
        return appointment.patient_id == user.patient_id
    return False

def check_patient_access(user, patient):
    """Check if user can access specific patient"""
    if user.role == UserRole.ADMIN:
        return True
    elif user.role == UserRole.PATIENT:
        # Patient can only access their own record
        return patient.patient_id == user.patient_id
    elif user.role == UserRole.DOCTOR:
        # Doctors can access patients they have appointments with
        # This would need additional logic to check appointments
        return True  # For now, allow doctors to see all patients
    return False

def check_doctor_access(user, doctor):
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