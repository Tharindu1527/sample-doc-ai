import logging
import subprocess
import sys
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback
from datetime import datetime

from config import settings

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("doctalk.log", encoding='utf-8') if not settings.debug else logging.NullHandler()
    ]
)

# Set console output encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up DocTalk AI backend with authentication...")
    try:
        from database.mongodb import connect_to_mongo
        await connect_to_mongo()
        logger.info("Database connection established")
        
        # Create default admin user if not exists
        try:
            from services.auth_service import auth_service
            from models.user import UserCreate, UserRole
            
            admin_exists = await auth_service.get_user_by_email("admin@doctalk.com")
            if not admin_exists:
                admin_user = UserCreate(
                    email="admin@doctalk.com",
                    password="password123",
                    role=UserRole.ADMIN,
                    first_name="Admin",
                    last_name="User",
                    department="Administration"
                )
                await auth_service.register_user(admin_user)
                logger.info("Default admin user created: admin@doctalk.com")
            
            # Create demo doctor
            doctor_exists = await auth_service.get_user_by_email("doctor@doctalk.com")
            if not doctor_exists:
                doctor_user = UserCreate(
                    email="doctor@doctalk.com",
                    password="password123",
                    role=UserRole.DOCTOR,
                    first_name="John",
                    last_name="Smith",
                    phone="+1-555-0123",
                    department="Internal Medicine"
                )
                await auth_service.register_user(doctor_user)
                logger.info("Demo doctor user created: doctor@doctalk.com")
            
            # Create demo patient
            patient_exists = await auth_service.get_user_by_email("patient@doctalk.com")
            if not patient_exists:
                patient_user = UserCreate(
                    email="patient@doctalk.com",
                    password="password123",
                    role=UserRole.PATIENT,
                    first_name="Jane",
                    last_name="Doe",
                    phone="+1-555-0456"
                )
                await auth_service.register_user(patient_user)
                logger.info("Demo patient user created: patient@doctalk.com")
                
        except Exception as e:
            logger.warning(f"Could not create default users: {e}")
        
        # Initialize enhanced voice service
        try:
            from services.voice_service import voice_service
            health = voice_service.health_check()
            logger.info(f"Enhanced voice service initialized: {health}")
        except Exception as e:
            logger.warning(f"Enhanced voice service initialization failed: {e}")
        
        # Only validate API keys in production
        if not settings.debug:
            try:
                settings.validate_api_keys()
            except ValueError as e:
                logger.warning(f"API key validation failed: {e}")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        logger.error(traceback.format_exc())
    
    yield
    
    # Shutdown
    logger.info("Shutting down DocTalk AI backend...")
    try:
        from database.mongodb import close_mongo_connection
        await close_mongo_connection()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="DocTalk AI",
    description="Real-Time GP Booking Voice Agent API with Authentication and Role-Based Access Control",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with proper error handling
def safe_include_router(router_path: str, router_name: str, prefix: str = "/api"):
    """Safely include a router with error handling"""
    try:
        module = __import__(router_path, fromlist=[router_name])
        router = getattr(module, router_name)
        app.include_router(router, prefix=prefix)
        logger.info(f"✓ {router_name} loaded successfully")  # Using check mark that should work
        return True
    except Exception as e:
        logger.error(f"✗ Failed to load {router_name}: {e}")  # Using X mark that should work
        return False

# Load authentication router first
safe_include_router("api.auth", "router", "/api")

# Load protected routers
safe_include_router("api.appointments_protected", "router", "/api")
safe_include_router("api.patients", "router", "/api")
safe_include_router("api.doctors", "router", "/api")

# Include the enhanced voice router
try:
    from api.voice import router as enhanced_voice_router
    app.include_router(enhanced_voice_router, prefix="/api")
    logger.info("✓ Enhanced voice router loaded successfully")
except Exception as e:
    logger.error(f"✗ Failed to load enhanced voice router: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to DocTalk AI - Medical Practice Management with Authentication",
        "version": "2.0.0",
        "features": [
            "User authentication and authorization",
            "Role-based access control (Admin, Doctor, Patient)",
            "Real-time voice interaction",
            "Database-driven doctor recommendations", 
            "Live appointment booking",
            "Real patient data integration",
            "Enhanced AI responses"
        ],
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "health": "/health",
        "auth": "/api/auth",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with authentication status"""
    try:
        # Test database connection
        from database.mongodb import get_database, health_check as db_health
        db_status = "disconnected"
        db_stats = {}
        
        try:
            if await db_health():
                db_status = "connected"
                
                # Get database statistics
                db = get_database()
                collections = await db.list_collection_names()
                db_stats = {}
                for collection_name in collections:
                    count = await db[collection_name].count_documents({})
                    db_stats[collection_name] = count
                    
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Test enhanced voice service
        voice_health = {"status": "unavailable"}
        try:
            from services.voice_service import voice_service
            voice_health = voice_service.health_check()
            
            # Add real-time data stats
            try:
                doctors = await voice_service.get_real_doctors_data()
                voice_health["real_time_stats"] = {
                    "available_doctors": len([d for d in doctors if d['is_available']]),
                    "total_doctors": len(doctors),
                    "specialties": len(set([d['specialty'] for d in doctors]))
                }
            except Exception as e:
                voice_health["real_time_stats"] = {"error": str(e)}
                
        except Exception as e:
            logger.error(f"Voice service health check failed: {e}")
        
        # Test authentication service
        auth_health = {"status": "unavailable"}
        try:
            from services.auth_service import auth_service
            # Try to get user count
            db = get_database()
            user_count = await db["users"].count_documents({})
            auth_health = {
                "status": "available",
                "total_users": user_count,
                "jwt_configured": bool(auth_service.secret_key)
            }
        except Exception as e:
            logger.error(f"Auth service health check failed: {e}")
        
        return {
            "status": "healthy",
            "message": "DocTalk AI backend is running with authentication",
            "version": "2.0.0",
            "database": {
                "status": db_status,
                "collections": db_stats
            },
            "authentication": auth_health,
            "voice_service": voice_health,
            "features": {
                "authentication": auth_health["status"] == "available",
                "real_time_data": db_status == "connected",
                "voice_ai": voice_health.get("gemini") == "available",
                "speech_recognition": voice_health.get("deepgram") == "available",
                "text_to_speech": voice_health.get("elevenlabs") == "available"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# Enhanced admin endpoints for development
@app.post("/api/admin/create-sample-data")
async def create_sample_data():
    """Create sample data for testing"""
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Admin endpoints disabled in production")
    
    try:
        from create_sample_data import create_quick_sample_data
        result = await create_quick_sample_data()
        
        # Test enhanced voice service with new data
        try:
            from services.voice_service import voice_service
            doctors = await voice_service.get_real_doctors_data()
            patients = await voice_service.get_real_patients_data()
            
            return {
                "message": "Sample data created successfully", 
                "result": result,
                "voice_service_test": {
                    "doctors_loaded": len(doctors),
                    "patients_loaded": len(patients),
                    "integration_status": "working" if doctors and patients else "partial"
                }
            }
        except Exception as e:
            return {
                "message": "Sample data created successfully", 
                "result": result,
                "voice_service_test": {"error": str(e)}
            }
            
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to create sample data: {str(e)}"}
        )

# Rest of your existing endpoints...
@app.post("/api/admin/create-demo-users")
async def create_demo_users():
    """Create demo users for testing"""
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Admin endpoints disabled in production")
    
    try:
        from services.auth_service import auth_service
        from models.user import UserCreate, UserRole
        
        demo_users = [
            {
                "email": "admin@doctalk.com",
                "password": "password123",
                "role": UserRole.ADMIN,
                "first_name": "Admin",
                "last_name": "User",
                "department": "Administration"
            },
            {
                "email": "doctor@doctalk.com",
                "password": "password123",
                "role": UserRole.DOCTOR,
                "first_name": "John",
                "last_name": "Smith",
                "phone": "+1-555-0123",
                "department": "Internal Medicine"
            },
            {
                "email": "patient@doctalk.com",
                "password": "password123",
                "role": UserRole.PATIENT,
                "first_name": "Jane",
                "last_name": "Doe",
                "phone": "+1-555-0456"
            }
        ]
        
        created_users = []
        for user_data in demo_users:
            try:
                existing = await auth_service.get_user_by_email(user_data["email"])
                if not existing:
                    user = UserCreate(**user_data)
                    created_user = await auth_service.register_user(user)
                    created_users.append({
                        "email": created_user.email,
                        "role": created_user.role,
                        "status": "created"
                    })
                else:
                    created_users.append({
                        "email": user_data["email"],
                        "role": user_data["role"],
                        "status": "already_exists"
                    })
            except Exception as e:
                created_users.append({
                    "email": user_data["email"],
                    "role": user_data["role"],
                    "status": f"error: {str(e)}"
                })
        
        return {
            "message": "Demo users creation completed",
            "users": created_users
        }
        
    except Exception as e:
        logger.error(f"Error creating demo users: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error creating demo users: {str(e)}"}
        )

@app.get("/api/admin/database-stats")
async def get_database_stats():
    """Get enhanced database statistics"""
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Admin endpoints disabled in production")
    
    try:
        from database.mongodb import get_database
        
        db = get_database()
        collections = await db.list_collection_names()
        
        stats = {}
        for collection_name in collections:
            collection = db[collection_name]
            count = await collection.count_documents({})
            stats[collection_name] = count
        
        # Add authentication stats
        auth_stats = {}
        if "users" in collections:
            from models.user import UserRole
            for role in UserRole:
                count = await db["users"].count_documents({"role": role.value})
                auth_stats[f"{role.value}_users"] = count
        
        # Add voice service integration stats
        try:
            from services.voice_service import voice_service
            doctors = await voice_service.get_real_doctors_data()
            voice_stats = {
                "available_doctors": len([d for d in doctors if d['is_available']]),
                "total_doctors": len(doctors),
                "unique_specialties": len(set([d['specialty'] for d in doctors])),
                "voice_service_status": "operational"
            }
        except Exception as e:
            voice_stats = {
                "voice_service_status": "error",
                "error": str(e)
            }
        
        return {
            "message": "Enhanced database statistics retrieved",
            "collections": stats,
            "authentication": auth_stats,
            "total_collections": len(collections),
            "voice_integration": voice_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting database stats: {str(e)}"}
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception on {request.url}: {exc}")
    logger.error(traceback.format_exc())
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "url": str(request.url),
                "traceback": traceback.format_exc()
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting DocTalk AI backend with authentication on {settings.host}:{settings.port}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"CORS origins: {settings.cors_origins}")
    logger.info("Features: User Authentication, Role-based Access Control, Real-time database integration, Enhanced voice AI")
    
    # Check if required directories exist
    os.makedirs("logs", exist_ok=True)
    
    try:
        uvicorn.run(
            "main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info" if not settings.debug else "debug",
            access_log=True,
            use_colors=True,
            reload_dirs=["./"] if settings.debug else None,
            # Connection management
            timeout_keep_alive=30,
            timeout_graceful_shutdown=30
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)