from datetime import datetime, time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from models.doctor import Doctor, DoctorCreate, DoctorUpdate, DoctorResponse, WorkingHours
from database.mongodb import get_database
import logging
import uuid

logger = logging.getLogger(__name__)

class DoctorService:
    def __init__(self):
        self.collection_name = "doctors"

    def _serialize_doctor_for_mongo(self, doctor_dict: dict) -> dict:
        """Convert doctor data for MongoDB storage"""
        if 'working_hours' in doctor_dict and doctor_dict['working_hours']:
            for wh in doctor_dict['working_hours']:
                # Convert time objects to string format for MongoDB
                if isinstance(wh.get('start_time'), time):
                    wh['start_time'] = wh['start_time'].strftime('%H:%M:%S')
                if isinstance(wh.get('end_time'), time):
                    wh['end_time'] = wh['end_time'].strftime('%H:%M:%S')
        return doctor_dict

    def _deserialize_doctor_from_mongo(self, doctor_data: dict) -> dict:
        """Convert doctor data from MongoDB"""
        if 'working_hours' in doctor_data and doctor_data['working_hours']:
            for wh in doctor_data['working_hours']:
                # Convert string back to time objects
                if isinstance(wh.get('start_time'), str):
                    try:
                        wh['start_time'] = datetime.strptime(wh['start_time'], '%H:%M:%S').time()
                    except ValueError:
                        wh['start_time'] = datetime.strptime(wh['start_time'], '%H:%M').time()
                if isinstance(wh.get('end_time'), str):
                    try:
                        wh['end_time'] = datetime.strptime(wh['end_time'], '%H:%M:%S').time()
                    except ValueError:
                        wh['end_time'] = datetime.strptime(wh['end_time'], '%H:%M').time()
        return doctor_data

    async def create_doctor(self, doctor_data: DoctorCreate) -> DoctorResponse:
        """Create a new doctor"""
        try:
            db = get_database()
            
            # Generate unique doctor ID
            doctor_id = f"D{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
            
            # Create doctor with generated ID
            doctor_dict = doctor_data.dict()
            doctor_dict['doctor_id'] = doctor_id
            
            # Set default working hours if not provided
            if not doctor_dict.get('working_hours'):
                doctor_dict['working_hours'] = [
                    {"day": "Monday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Tuesday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Wednesday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Thursday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Friday", "start_time": "09:00:00", "end_time": "17:00:00", "is_available": True},
                    {"day": "Saturday", "start_time": "09:00:00", "end_time": "13:00:00", "is_available": False},
                    {"day": "Sunday", "start_time": "09:00:00", "end_time": "13:00:00", "is_available": False}
                ]
            
            # Serialize for MongoDB
            mongo_doctor_dict = self._serialize_doctor_for_mongo(doctor_dict.copy())
            
            # Add timestamps and default values
            mongo_doctor_dict['created_at'] = datetime.utcnow()
            mongo_doctor_dict['updated_at'] = datetime.utcnow()
            
            # Set default values for required fields if not provided
            if 'total_reviews' not in mongo_doctor_dict:
                mongo_doctor_dict['total_reviews'] = 0
            if 'rating' not in mongo_doctor_dict:
                mongo_doctor_dict['rating'] = None
            if 'is_active' not in mongo_doctor_dict:
                mongo_doctor_dict['is_active'] = True
            if 'is_available' not in mongo_doctor_dict:
                mongo_doctor_dict['is_available'] = True
            
            result = await db[self.collection_name].insert_one(mongo_doctor_dict)
            
            created_doctor = await db[self.collection_name].find_one({"_id": result.inserted_id})
            
            # Deserialize from MongoDB
            created_doctor = self._deserialize_doctor_from_mongo(created_doctor)
            
            return DoctorResponse(
                id=str(created_doctor["_id"]),
                **{k: v for k, v in created_doctor.items() if k != "_id"}
            )
        except Exception as e:
            logger.error(f"Error creating doctor: {e}")
            raise

    async def get_doctor(self, doctor_id: str) -> Optional[DoctorResponse]:
        """Get doctor by ID or doctor_id"""
        try:
            db = get_database()
            
            # Try to find by ObjectId first, then by doctor_id
            query = {"doctor_id": doctor_id}
            if ObjectId.is_valid(doctor_id):
                query = {"$or": [{"_id": ObjectId(doctor_id)}, {"doctor_id": doctor_id}]}
            
            doctor = await db[self.collection_name].find_one(query)
            
            if doctor:
                # Deserialize from MongoDB
                doctor = self._deserialize_doctor_from_mongo(doctor)
                
                return DoctorResponse(
                    id=str(doctor["_id"]),
                    **{k: v for k, v in doctor.items() if k != "_id"}
                )
            return None
        except Exception as e:
            logger.error(f"Error getting doctor: {e}")
            raise

    async def get_all_doctors(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[DoctorResponse]:
        """Get all doctors with pagination"""
        try:
            db = get_database()
            
            query = {}
            if active_only:
                query["is_active"] = True
            
            cursor = db[self.collection_name].find(query).skip(skip).limit(limit).sort("last_name", 1)
            doctors = await cursor.to_list(length=limit)
            
            result = []
            for doctor in doctors:
                # Deserialize from MongoDB
                doctor = self._deserialize_doctor_from_mongo(doctor)
                result.append(DoctorResponse(
                    id=str(doctor["_id"]),
                    **{k: v for k, v in doctor.items() if k != "_id"}
                ))
            
            return result
        except Exception as e:
            logger.error(f"Error getting doctors: {e}")
            raise

    async def get_available_doctors(self, specialty: str = None) -> List[DoctorResponse]:
        """Get available doctors, optionally filtered by specialty"""
        try:
            db = get_database()
            
            query = {"is_active": True, "is_available": True}
            if specialty:
                query["specialty"] = {"$regex": specialty, "$options": "i"}
            
            cursor = db[self.collection_name].find(query).sort("last_name", 1)
            doctors = await cursor.to_list(length=None)
            
            result = []
            for doctor in doctors:
                # Deserialize from MongoDB
                doctor = self._deserialize_doctor_from_mongo(doctor)
                result.append(DoctorResponse(
                    id=str(doctor["_id"]),
                    **{k: v for k, v in doctor.items() if k != "_id"}
                ))
            
            return result
        except Exception as e:
            logger.error(f"Error getting available doctors: {e}")
            raise

    async def update_doctor(self, doctor_id: str, update_data: DoctorUpdate) -> Optional[DoctorResponse]:
        """Update a doctor"""
        try:
            db = get_database()
            
            # Build query
            query = {"doctor_id": doctor_id}
            if ObjectId.is_valid(doctor_id):
                query = {"$or": [{"_id": ObjectId(doctor_id)}, {"doctor_id": doctor_id}]}
            
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            update_dict["updated_at"] = datetime.utcnow()
            
            # Serialize for MongoDB
            update_dict = self._serialize_doctor_for_mongo(update_dict)
            
            result = await db[self.collection_name].update_one(
                query,
                {"$set": update_dict}
            )
            
            if result.modified_count:
                updated_doctor = await db[self.collection_name].find_one(query)
                # Deserialize from MongoDB
                updated_doctor = self._deserialize_doctor_from_mongo(updated_doctor)
                
                return DoctorResponse(
                    id=str(updated_doctor["_id"]),
                    **{k: v for k, v in updated_doctor.items() if k != "_id"}
                )
            return None
        except Exception as e:
            logger.error(f"Error updating doctor: {e}")
            raise

    async def deactivate_doctor(self, doctor_id: str) -> bool:
        """Deactivate a doctor (soft delete)"""
        try:
            db = get_database()
            
            query = {"doctor_id": doctor_id}
            if ObjectId.is_valid(doctor_id):
                query = {"$or": [{"_id": ObjectId(doctor_id)}, {"doctor_id": doctor_id}]}
            
            result = await db[self.collection_name].update_one(
                query,
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error deactivating doctor: {e}")
            return False

    async def search_doctors(self, query: str = "", filters: Dict[str, Any] = None) -> List[DoctorResponse]:
        """Search doctors with text query and filters"""
        try:
            db = get_database()
            
            # Build MongoDB query
            mongo_query = {}
            
            # Text search
            if query:
                mongo_query["$or"] = [
                    {"first_name": {"$regex": query, "$options": "i"}},
                    {"last_name": {"$regex": query, "$options": "i"}},
                    {"specialty": {"$regex": query, "$options": "i"}},
                    {"department": {"$regex": query, "$options": "i"}},
                    {"doctor_id": {"$regex": query, "$options": "i"}}
                ]
            
            # Apply filters
            if filters:
                if filters.get('is_active') is not None:
                    mongo_query['is_active'] = filters['is_active']
                if filters.get('is_available') is not None:
                    mongo_query['is_available'] = filters['is_available']
                if filters.get('specialty'):
                    mongo_query['specialty'] = {"$regex": filters['specialty'], "$options": "i"}
                if filters.get('department'):
                    mongo_query['department'] = {"$regex": filters['department'], "$options": "i"}
                if filters.get('min_experience'):
                    mongo_query['years_experience'] = {"$gte": int(filters['min_experience'])}
            
            cursor = db[self.collection_name].find(mongo_query).sort("last_name", 1)
            doctors = await cursor.to_list(length=100)  # Limit to 100 results
            
            result = []
            for doctor in doctors:
                # Deserialize from MongoDB
                doctor = self._deserialize_doctor_from_mongo(doctor)
                result.append(DoctorResponse(
                    id=str(doctor["_id"]),
                    **{k: v for k, v in doctor.items() if k != "_id"}
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching doctors: {e}")
            return []

    async def get_doctor_by_name(self, name: str) -> Optional[DoctorResponse]:
        """Find doctor by name (used for voice appointments)"""
        try:
            db = get_database()
            
            # Remove "Dr." prefix if present and clean name
            clean_name = name.replace("Dr.", "").replace("Doctor", "").strip()
            
            # Search for exact match first, then partial
            queries = [
                # Exact last name match
                {"last_name": {"$regex": f"^{clean_name}$", "$options": "i"}},
                # Partial last name match
                {"last_name": {"$regex": clean_name, "$options": "i"}},
                # Full name search
                {"$or": [
                    {"first_name": {"$regex": clean_name, "$options": "i"}},
                    {"last_name": {"$regex": clean_name, "$options": "i"}}
                ]}
            ]
            
            for query in queries:
                query["is_active"] = True
                query["is_available"] = True
                doctor = await db[self.collection_name].find_one(query)
                if doctor:
                    # Deserialize from MongoDB
                    doctor = self._deserialize_doctor_from_mongo(doctor)
                    
                    return DoctorResponse(
                        id=str(doctor["_id"]),
                        **{k: v for k, v in doctor.items() if k != "_id"}
                    )
            
            return None
        except Exception as e:
            logger.error(f"Error finding doctor by name: {e}")
            return None

    async def get_doctor_statistics(self) -> Dict[str, Any]:
        """Get doctor statistics for dashboard"""
        try:
            db = get_database()
            
            stats = {}
            
            # Total doctors
            stats['total_doctors'] = await db[self.collection_name].count_documents({"is_active": True})
            
            # Available doctors
            stats['available_doctors'] = await db[self.collection_name].count_documents({
                "is_active": True,
                "is_available": True
            })
            
            # Specialty distribution
            specialty_pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {"_id": "$specialty", "count": {"$sum": 1}}}
            ]
            specialty_results = await db[self.collection_name].aggregate(specialty_pipeline).to_list(length=None)
            stats['by_specialty'] = {item['_id']: item['count'] for item in specialty_results}
            
            # Department distribution
            department_pipeline = [
                {"$match": {"is_active": True, "department": {"$ne": None}}},
                {"$group": {"_id": "$department", "count": {"$sum": 1}}}
            ]
            department_results = await db[self.collection_name].aggregate(department_pipeline).to_list(length=None)
            stats['by_department'] = {item['_id']: item['count'] for item in department_results}
            
            # Experience distribution
            experience_pipeline = [
                {"$match": {"is_active": True, "years_experience": {"$exists": True}}},
                {
                    "$group": {
                        "_id": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$lt": ["$years_experience", 5]}, "then": "0-4 years"},
                                    {"case": {"$and": [{"$gte": ["$years_experience", 5]}, {"$lt": ["$years_experience", 10]}]}, "then": "5-9 years"},
                                    {"case": {"$and": [{"$gte": ["$years_experience", 10]}, {"$lt": ["$years_experience", 20]}]}, "then": "10-19 years"},
                                    {"case": {"$gte": ["$years_experience", 20]}, "then": "20+ years"}
                                ],
                                "default": "Unknown"
                            }
                        },
                        "count": {"$sum": 1}
                    }
                }
            ]
            experience_results = await db[self.collection_name].aggregate(experience_pipeline).to_list(length=None)
            stats['by_experience'] = {item['_id']: item['count'] for item in experience_results}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting doctor statistics: {e}")
            return {}

# Create global instance
doctor_service = DoctorService()

# Rest of the router code remains the same...
router = APIRouter(prefix="/doctors", tags=["doctors"])

# SPECIFIC ROUTES FIRST
@router.get("/statistics", response_model=dict)
async def get_doctor_statistics():
    """Get doctor statistics for dashboard"""
    try:
        result = await doctor_service.get_doctor_statistics()
        return result
    except Exception as e:
        logger.error(f"Error getting doctor statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get doctor statistics")

@router.get("/search", response_model=List[DoctorResponse])
async def search_doctors(
    q: str = Query("", description="Search query"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    department: Optional[str] = Query(None, description="Filter by department"),
    min_experience: Optional[int] = Query(None, description="Minimum years of experience"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """Search doctors with filters"""
    try:
        filters = {}
        if specialty:
            filters['specialty'] = specialty
        if department:
            filters['department'] = department
        if min_experience is not None:
            filters['min_experience'] = min_experience
        if is_available is not None:
            filters['is_available'] = is_available
        if is_active is not None:
            filters['is_active'] = is_active
            
        result = await doctor_service.search_doctors(query=q, filters=filters)
        return result
    except Exception as e:
        logger.error(f"Error searching doctors: {e}")
        raise HTTPException(status_code=500, detail="Failed to search doctors")

@router.get("/available", response_model=List[DoctorResponse])
async def get_available_doctors(
    specialty: Optional[str] = Query(None, description="Filter by specialty")
):
    """Get available doctors, optionally filtered by specialty"""
    try:
        result = await doctor_service.get_available_doctors(specialty=specialty)
        return result
    except Exception as e:
        logger.error(f"Error getting available doctors: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available doctors")

@router.get("/find/by-name", response_model=DoctorResponse)
async def find_doctor_by_name(
    name: str = Query(..., description="Doctor name")
):
    """Find doctor by name (for voice appointments)"""
    try:
        result = await doctor_service.get_doctor_by_name(name)
        if not result:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding doctor: {e}")
        raise HTTPException(status_code=500, detail="Failed to find doctor")

@router.get("/", response_model=List[DoctorResponse])
async def get_all_doctors(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    active_only: bool = Query(True, description="Return only active doctors")
):
    """Get all doctors with pagination"""
    try:
        result = await doctor_service.get_all_doctors(skip=skip, limit=limit, active_only=active_only)
        return result
    except Exception as e:
        logger.error(f"Error getting doctors: {e}")
        raise HTTPException(status_code=500, detail="Failed to get doctors")

@router.post("/", response_model=DoctorResponse)
async def create_doctor(doctor: DoctorCreate):
    """Create a new doctor"""
    try:
        result = await doctor_service.create_doctor(doctor)
        return result
    except Exception as e:
        logger.error(f"Error creating doctor: {e}")
        raise HTTPException(status_code=500, detail="Failed to create doctor")

# PARAMETERIZED ROUTES LAST
@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(doctor_id: str):
    """Get doctor by ID"""
    try:
        result = await doctor_service.get_doctor(doctor_id)
        if not result:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting doctor: {e}")
        raise HTTPException(status_code=500, detail="Failed to get doctor")

@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(doctor_id: str, update_data: DoctorUpdate):
    """Update a doctor"""
    try:
        result = await doctor_service.update_doctor(doctor_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating doctor: {e}")
        raise HTTPException(status_code=500, detail="Failed to update doctor")

@router.delete("/{doctor_id}")
async def deactivate_doctor(doctor_id: str):
    """Deactivate a doctor (soft delete)"""
    try:
        success = await doctor_service.deactivate_doctor(doctor_id)
        if not success:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return {"message": "Doctor deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating doctor: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate doctor")