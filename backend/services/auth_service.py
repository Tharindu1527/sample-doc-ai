# backend/services/auth_service.py
import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from bson import ObjectId
from models.user import User, UserCreate, UserUpdate, UserResponse, UserRole
from database.mongodb import get_database
from config import settings
import logging

# Fix JWT import - use PyJWT directly
try:
    import jwt
except ImportError:
    try:
        from jose import jwt
        # If using python-jose, we need to import differently
        from jose.exceptions import JWTError as PyJWTError
    except ImportError:
        raise ImportError("Neither PyJWT nor python-jose is available. Please install one of them.")

# Handle different JWT libraries
try:
    from jwt.exceptions import PyJWTError
except ImportError:
    try:
        from jose.exceptions import JWTError as PyJWTError
    except ImportError:
        # Fallback for older versions
        PyJWTError = Exception

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.collection_name = "users"
        self.secret_key = getattr(settings, 'jwt_secret_key', 'your-secret-key-change-this-in-production')
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 30

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def _generate_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Generate JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        
        try:
            # Try PyJWT first
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"JWT encoding error: {e}")
            # If PyJWT fails, try python-jose
            try:
                from jose import jwt as jose_jwt
                return jose_jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            except Exception as jose_error:
                logger.error(f"JOSE JWT encoding error: {jose_error}")
                raise Exception(f"Failed to encode JWT token: {e}")

    def _decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token"""
        try:
            # Try PyJWT first
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except PyJWTError as e:
            logger.error(f"JWT decoding error with PyJWT: {e}")
        except Exception as e:
            logger.error(f"General JWT decoding error: {e}")
            
        # If PyJWT fails, try python-jose
        try:
            from jose import jwt as jose_jwt
            from jose.exceptions import JWTError
            payload = jose_jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.error(f"JWT decoding error with python-jose: {e}")
        except Exception as e:
            logger.error(f"General JOSE decoding error: {e}")
            
        return None

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """Register a new user"""
        try:
            db = get_database()
            
            # Check if user already exists
            existing_user = await db[self.collection_name].find_one({"email": user_data.email})
            if existing_user:
                raise ValueError("User with this email already exists")
            
            # Generate unique user ID
            user_id = f"U{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
            
            # Hash password
            password_hash = self._hash_password(user_data.password)
            
            # Create user document
            user_dict = user_data.dict(exclude={'password'})
            user_dict.update({
                'user_id': user_id,
                'password_hash': password_hash,
                'is_active': True,
                'is_verified': False,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            # Create corresponding doctor/patient record if needed
            if user_data.role == UserRole.DOCTOR:
                user_dict['doctor_id'] = await self._create_doctor_record(user_dict)
            elif user_data.role == UserRole.PATIENT:
                user_dict['patient_id'] = await self._create_patient_record(user_dict)
            
            result = await db[self.collection_name].insert_one(user_dict)
            
            created_user = await db[self.collection_name].find_one({"_id": result.inserted_id})
            
            logger.info(f"User registered successfully: {user_data.email}")
            
            return UserResponse(
                id=str(created_user["_id"]),
                **{k: v for k, v in created_user.items() if k != "_id"}
            )
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            raise

    async def _create_doctor_record(self, user_dict: dict) -> str:
        """Create corresponding doctor record"""
        try:
            db = get_database()
            
            doctor_id = f"D{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
            
            doctor_data = {
                'doctor_id': doctor_id,
                'first_name': user_dict['first_name'],
                'last_name': user_dict['last_name'],
                'title': 'Dr.',
                'specialty': user_dict.get('department', 'General Practice'),
                'department': user_dict.get('department', 'General'),
                'email': user_dict['email'],
                'phone': user_dict.get('phone'),
                'is_available': True,
                'is_active': True,
                'total_reviews': 0,
                'working_hours': [
                    {"day": "Monday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Tuesday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Wednesday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Thursday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Friday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Saturday", "start_time": "09:00:00", "end_time": "13:00:00", "is_available": False},
                    {"day": "Sunday", "start_time": "09:00:00", "end_time": "13:00:00", "is_available": False}
                ],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            await db["doctors"].insert_one(doctor_data)
            logger.info(f"Doctor record created: {doctor_id}")
            return doctor_id
            
        except Exception as e:
            logger.error(f"Error creating doctor record: {e}")
            raise

    async def _create_patient_record(self, user_dict: dict) -> str:
        """Create corresponding patient record"""
        try:
            db = get_database()
            
            patient_id = f"P{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
            
            patient_data = {
                'patient_id': patient_id,
                'first_name': user_dict['first_name'],
                'last_name': user_dict['last_name'],
                'email': user_dict['email'],
                'phone': user_dict.get('phone'),
                'is_active': True,
                'medical_history': [],
                'allergies': [],
                'medications': [],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            await db["patients"].insert_one(patient_data)
            logger.info(f"Patient record created: {patient_id}")
            return patient_id
            
        except Exception as e:
            logger.error(f"Error creating patient record: {e}")
            raise

    async def authenticate_user(self, email: str, password: str) -> Optional[UserResponse]:
        """Authenticate user with email and password"""
        try:
            db = get_database()
            
            user = await db[self.collection_name].find_one({"email": email})
            if not user:
                logger.warning(f"User not found: {email}")
                return None
            
            if not self._verify_password(password, user['password_hash']):
                logger.warning(f"Invalid password for user: {email}")
                return None
            
            if not user['is_active']:
                raise ValueError("Account is deactivated")
            
            # Update last login
            await db[self.collection_name].update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            
            logger.info(f"User authenticated successfully: {email}")
            
            return UserResponse(
                id=str(user["_id"]),
                **{k: v for k, v in user.items() if k not in ["_id", "password_hash"]}
            )
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    async def create_tokens(self, user: UserResponse) -> Dict[str, Any]:
        """Create access and refresh tokens"""
        try:
            access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
            refresh_token_expires = timedelta(days=self.refresh_token_expire_days)
            
            access_token_data = {
                "sub": user.email,
                "user_id": user.user_id,
                "role": user.role,
                "type": "access"
            }
            
            refresh_token_data = {
                "sub": user.email,
                "user_id": user.user_id,
                "type": "refresh"
            }
            
            access_token = self._generate_token(access_token_data, access_token_expires)
            refresh_token = self._generate_token(refresh_token_data, refresh_token_expires)
            
            logger.info(f"Tokens created for user: {user.email}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60
            }
        except Exception as e:
            logger.error(f"Error creating tokens: {e}")
            raise

    async def get_current_user(self, token: str) -> Optional[UserResponse]:
        """Get current user from token"""
        try:
            payload = self._decode_token(token)
            if not payload:
                return None
            
            if payload.get("type") != "access":
                return None
            
            email = payload.get("sub")
            if not email:
                return None
            
            db = get_database()
            user = await db[self.collection_name].find_one({"email": email})
            
            if not user or not user['is_active']:
                return None
            
            return UserResponse(
                id=str(user["_id"]),
                **{k: v for k, v in user.items() if k not in ["_id", "password_hash"]}
            )
            
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return None

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token"""
        try:
            payload = self._decode_token(refresh_token)
            if not payload or payload.get("type") != "refresh":
                return None
            
            email = payload.get("sub")
            user = await self.get_user_by_email(email)
            
            if not user:
                return None
            
            return await self.create_tokens(user)
            
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email"""
        try:
            db = get_database()
            user = await db[self.collection_name].find_one({"email": email})
            
            if not user:
                return None
            
            return UserResponse(
                id=str(user["_id"]),
                **{k: v for k, v in user.items() if k not in ["_id", "password_hash"]}
            )
            
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            db = get_database()
            
            user = await db[self.collection_name].find_one({"user_id": user_id})
            if not user:
                return False
            
            if not self._verify_password(current_password, user['password_hash']):
                return False
            
            new_password_hash = self._hash_password(new_password)
            
            result = await db[self.collection_name].update_one(
                {"user_id": user_id},
                {"$set": {"password_hash": new_password_hash, "updated_at": datetime.utcnow()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False

    async def update_user(self, user_id: str, update_data: UserUpdate) -> Optional[UserResponse]:
        """Update user information"""
        try:
            db = get_database()
            
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await db[self.collection_name].update_one(
                {"user_id": user_id},
                {"$set": update_dict}
            )
            
            if result.modified_count:
                user = await db[self.collection_name].find_one({"user_id": user_id})
                return UserResponse(
                    id=str(user["_id"]),
                    **{k: v for k, v in user.items() if k not in ["_id", "password_hash"]}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise

# Global instance
auth_service = AuthService()