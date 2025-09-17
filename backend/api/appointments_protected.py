# backend/api/appointments_protected.py
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from models.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from models.user import UserResponse, UserRole
from services.appointment_service import appointment_service
from api.auth import get_current_user, require_role
from middleware.auth_middleware import check_appointment_access
from database.mongodb import get_database
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.get("/statistics")
async def get_appointment_statistics(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get appointment statistics based on user role"""
    try:
        if current_user.role == UserRole.ADMIN:
            # Admin sees all statistics
            result = await appointment_service.get_appointment_statistics()
        elif current_user.role == UserRole.DOCTOR:
            # Doctor sees only their statistics
            result = await appointment_service.get_doctor_appointment_statistics(
                f"Dr. {current_user.first_name} {current_user.last_name}"
            )
        elif current_user.role == UserRole.PATIENT:
            # Patient sees their appointment count
            result = await appointment_service.get_patient_appointment_statistics(
                current_user.patient_id
            )
        else:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return result
    except Exception as e:
        logger.error(f"Error getting appointment statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get appointment statistics")

@router.get("/search")
async def search_appointments(
    q: str = Query("", description="Search query"),
    status: Optional[str] = Query(None, description="Filter by status"),
    doctor: Optional[str] = Query(None, description="Filter by doctor"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    current_user: UserResponse = Depends(get_current_user)
):
    """Search appointments with role-based filtering"""
    try:
        filters = {}
        if status:
            filters['status'] = status
        if doctor:
            filters['doctor'] = doctor
        if date_from:
            filters['date_from'] = datetime.combine(date_from, datetime.min.time())
        if date_to:
            filters['date_to'] = datetime.combine(date_to, datetime.max.time())
        
        # Add role-based filters
        if current_user.role == UserRole.DOCTOR:
            filters['doctor'] = f"Dr. {current_user.first_name} {current_user.last_name}"
        elif current_user.role == UserRole.PATIENT:
            filters['patient_id'] = current_user.patient_id
        
        result = await appointment_service.search_appointments(query=q, filters=filters)
        
        # Filter results based on access control
        filtered_result = []
        for appointment in result:
            if check_appointment_access(current_user, appointment):
                filtered_result.append(appointment)
        
        return filtered_result
    except Exception as e:
        logger.error(f"Error searching appointments: {e}")
        raise HTTPException(status_code=500, detail="Failed to search appointments")

@router.get("/all")
async def get_all_appointments(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    include_cancelled: bool = Query(False, description="Include cancelled appointments"),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get appointments based on user role"""
    try:
        db = get_database()
        query = {}
        
        if not include_cancelled:
            query["status"] = {"$ne": "cancelled"}
        
        # Role-based filtering
        if current_user.role == UserRole.DOCTOR:
            query["doctor_name"] = f"Dr. {current_user.first_name} {current_user.last_name}"
        elif current_user.role == UserRole.PATIENT:
            query["patient_id"] = current_user.patient_id
        # Admin sees all appointments (no additional filter)
        
        cursor = db["appointments"].find(query).skip(skip).limit(limit).sort("appointment_date", -1)
        appointments = await cursor.to_list(length=limit)
        
        result = []
        for appointment in appointments:
            result.append(AppointmentResponse(
                id=str(appointment["_id"]),
                **{k: v for k, v in appointment.items() if k != "_id"}
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        raise HTTPException(status_code=500, detail="Failed to get appointments")

@router.post("/")
async def create_appointment(
    appointment: AppointmentCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new appointment with role-based validation"""
    try:
        # Validate based on user role
        if current_user.role == UserRole.PATIENT:
            # Patients can only book for themselves
            if not current_user.patient_id:
                raise HTTPException(status_code=400, detail="Patient ID not found")
            appointment.patient_id = current_user.patient_id
            appointment.patient_name = f"{current_user.first_name} {current_user.last_name}"
            appointment.patient_email = current_user.email
        elif current_user.role == UserRole.DOCTOR:
            # Doctors can book for patients but not for themselves
            if not appointment.patient_id:
                raise HTTPException(status_code=400, detail="Patient ID required")
        # Admin can create appointments for anyone
        
        result = await appointment_service.create_appointment(appointment)
        return result
    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create appointment")

@router.get("/patient/{patient_id}")
async def get_patient_appointments(
    patient_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get appointments for a patient with access control"""
    try:
        # Check access rights
        if current_user.role == UserRole.PATIENT:
            if patient_id != current_user.patient_id:
                raise HTTPException(status_code=403, detail="Access denied")
        elif current_user.role == UserRole.DOCTOR:
            # Doctors can only see appointments where they are the doctor
            # This will be filtered in the service
            pass
        # Admin can see all
        
        result = await appointment_service.get_appointments_by_patient(patient_id)
        
        # Filter for doctors to only show their appointments
        if current_user.role == UserRole.DOCTOR:
            doctor_name = f"Dr. {current_user.first_name} {current_user.last_name}"
            result = [apt for apt in result if apt.doctor_name == doctor_name]
        
        return result
    except Exception as e:
        logger.error(f"Error getting patient appointments: {e}")
        raise HTTPException(status_code=500, detail="Failed to get patient appointments")

@router.get("/doctor/{doctor_name}")
async def get_doctor_appointments(
    doctor_name: str,
    date: Optional[date] = Query(None, description="Filter by specific date"),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get appointments for a doctor with access control"""
    try:
        # Check access rights
        if current_user.role == UserRole.DOCTOR:
            expected_name = f"Dr. {current_user.first_name} {current_user.last_name}"
            if doctor_name != expected_name:
                raise HTTPException(status_code=403, detail="Access denied")
        elif current_user.role == UserRole.PATIENT:
            # Patients can view doctor's appointments (limited info)
            pass
        # Admin can see all
        
        filter_date = None
        if date:
            filter_date = datetime.combine(date, datetime.min.time())
        
        result = await appointment_service.get_appointments_by_doctor(doctor_name, filter_date)
        
        # If patient is viewing, hide sensitive information
        if current_user.role == UserRole.PATIENT:
            for appointment in result:
                appointment.patient_phone = "***-***-****"
                appointment.patient_email = "****@****.***"
                appointment.notes = None
        
        return result
    except Exception as e:
        logger.error(f"Error getting doctor appointments: {e}")
        raise HTTPException(status_code=500, detail="Failed to get doctor appointments")

@router.get("/availability/{doctor_name}")
async def get_available_slots(
    doctor_name: str,
    date: date = Query(..., description="Date to check availability"),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get available time slots for a doctor"""
    try:
        check_date = datetime.combine(date, datetime.min.time())
        slots = await appointment_service.get_available_slots(doctor_name, check_date)
        
        formatted_slots = [slot.strftime("%H:%M") for slot in slots]
        
        return {
            "doctor": doctor_name,
            "date": date.isoformat(),
            "available_slots": formatted_slots
        }
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available slots")

@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get appointment by ID with access control"""
    try:
        if len(appointment_id) != 24 or not all(c in '0123456789abcdefABCDEF' for c in appointment_id):
            raise HTTPException(status_code=400, detail="Invalid appointment ID format")
            
        result = await appointment_service.get_appointment(appointment_id)
        if not result:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        # Check access rights
        if not check_appointment_access(current_user, result):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appointment: {e}")
        raise HTTPException(status_code=500, detail="Failed to get appointment")

@router.put("/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    update_data: AppointmentUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update an appointment with role-based restrictions"""
    try:
        if len(appointment_id) != 24 or not all(c in '0123456789abcdefABCDEF' for c in appointment_id):
            raise HTTPException(status_code=400, detail="Invalid appointment ID format")
        
        # Get existing appointment to check access
        existing = await appointment_service.get_appointment(appointment_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        if not check_appointment_access(current_user, existing):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Role-based update restrictions
        if current_user.role == UserRole.PATIENT:
            # Patients can only update their own appointments and limited fields
            allowed_fields = ['appointment_date', 'notes', 'status']
            update_dict = {k: v for k, v in update_data.dict().items() 
                          if v is not None and k in allowed_fields}
            if update_dict.get('status') and update_dict['status'] not in ['scheduled', 'cancelled']:
                raise HTTPException(status_code=400, detail="Patients can only reschedule or cancel")
            update_data = AppointmentUpdate(**update_dict)
        
        result = await appointment_service.update_appointment(appointment_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        raise HTTPException(status_code=500, detail="Failed to update appointment")

@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Cancel an appointment with access control"""
    try:
        if len(appointment_id) != 24 or not all(c in '0123456789abcdefABCDEF' for c in appointment_id):
            raise HTTPException(status_code=400, detail="Invalid appointment ID format")
        
        # Get existing appointment to check access
        existing = await appointment_service.get_appointment(appointment_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        if not check_appointment_access(current_user, existing):
            raise HTTPException(status_code=403, detail="Access denied")
        
        result = await appointment_service.cancel_appointment(appointment_id)
        if not result:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return {"message": "Appointment cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel appointment")