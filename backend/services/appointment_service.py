from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bson import ObjectId
from models.appointment import Appointment, AppointmentCreate, AppointmentUpdate, AppointmentResponse
from models.patient import Patient, PatientCreate
from database.mongodb import get_database
import logging
import re
import uuid

logger = logging.getLogger(__name__)

class AppointmentService:
    def __init__(self):
        self.collection_name = "appointments"
        self.available_doctors = [
            "Dr. John Smith", "Dr. Sarah Johnson", "Dr. Michael Williams", "Dr. Emily Brown", 
            "Dr. David Davis", "Dr. Lisa Miller", "Dr. James Wilson", "Dr. Jennifer Moore"
        ]
        self.business_hours = {
            "start": 9,  # 9 AM
            "end": 17,   # 5 PM
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
        }

    async def handle_voice_appointment(self, intent: str, entities: Dict[str, Any], transcript: str, conversation_context: List[Dict]) -> Dict[str, Any]:
        """Handle appointment booking from voice commands with MongoDB integration"""
        try:
            logger.info(f"Handling voice appointment: intent={intent}, entities={entities}")
            
            if intent == "confirm_appointment":
                # Extract appointment details from conversation context and current entities
                appointment_data = await self._extract_appointment_from_context(entities, conversation_context)
                
                if appointment_data:
                    # Create or find patient
                    patient = await self._create_or_find_patient(appointment_data)
                    if not patient:
                        return {
                            'success': False,
                            'message': 'Sorry, I couldn\'t create the patient record. Please provide your full name and phone number.'
                        }
                    
                    # Create appointment
                    appointment = await self._create_appointment_from_voice(appointment_data, patient)
                    
                    if appointment:
                        return {
                            'success': True,
                            'message': f'Perfect! Your appointment with {appointment_data["doctor"]} on {appointment_data["date"]} at {appointment_data["time"]} has been confirmed. You\'ll receive a confirmation shortly.',
                            'appointment': appointment,
                            'patient': patient
                        }
                    else:
                        return {
                            'success': False,
                            'message': 'Sorry, I couldn\'t book that time slot. Let me check other available times for you.'
                        }
                else:
                    return {
                        'success': False,
                        'message': 'I need some more details to confirm your appointment. Please tell me your name, preferred doctor, date, and time.'
                    }
            
            elif intent == "book_appointment":
                # For initial booking intent, we collect information
                missing_info = []
                if not entities.get('patient_name'):
                    missing_info.append('your full name')
                if not entities.get('doctor'):
                    missing_info.append('preferred doctor')
                if not entities.get('date'):
                    missing_info.append('preferred date')
                if not entities.get('time'):
                    missing_info.append('preferred time')
                
                if missing_info:
                    return {
                        'success': False,
                        'message': f'I\'d be happy to help you book an appointment. I still need: {", ".join(missing_info)}. What would you like to tell me first?',
                        'missing': missing_info
                    }
                else:
                    # We have all info, ask for confirmation
                    return {
                        'success': False,
                        'message': f'Great! Let me confirm: {entities["patient_name"]}, appointment with {entities["doctor"]} on {entities["date"]} at {entities["time"]}. Should I book this for you?',
                        'needs_confirmation': True
                    }
            
            return {
                'success': False,
                'message': 'I can help you with booking appointments. Please tell me your name, preferred doctor, date, and time.'
            }
            
        except Exception as e:
            logger.error(f"Error handling voice appointment: {e}")
            return {
                'success': False,
                'message': 'Sorry, I encountered an error while processing your appointment. Please try again.'
            }

    async def _extract_appointment_from_context(self, current_entities: Dict[str, Any], conversation_context: List[Dict]) -> Optional[Dict[str, Any]]:
        """Extract complete appointment data from current entities and conversation context"""
        appointment_data = {}
        
        # Start with current entities
        if current_entities.get('patient_name'):
            appointment_data['patient_name'] = current_entities['patient_name']
        if current_entities.get('doctor'):
            appointment_data['doctor'] = current_entities['doctor']
        if current_entities.get('date'):
            appointment_data['date'] = current_entities['date']
        if current_entities.get('time'):
            appointment_data['time'] = current_entities['time']
        if current_entities.get('reason'):
            appointment_data['reason'] = current_entities['reason']
        if current_entities.get('phone'):
            appointment_data['phone'] = current_entities['phone']
        
        # Extract missing info from conversation context
        for context_item in reversed(conversation_context[-5:]):  # Look at last 5 exchanges
            user_text = context_item.get('user', '').lower()
            
            # Extract patient name patterns
            if not appointment_data.get('patient_name'):
                name_patterns = [
                    r"my name is ([a-zA-Z\s]+)",
                    r"i'm ([a-zA-Z\s]+)",
                    r"this is ([a-zA-Z\s]+)",
                    r"([a-zA-Z]+\s+[a-zA-Z]+)" # Basic first last name pattern
                ]
                for pattern in name_patterns:
                    match = re.search(pattern, user_text, re.IGNORECASE)
                    if match:
                        name = match.group(1).strip().title()
                        if len(name.split()) >= 2:  # At least first and last name
                            appointment_data['patient_name'] = name
                            break
            
            # Extract doctor preferences
            if not appointment_data.get('doctor'):
                for doctor in self.available_doctors:
                    doctor_variations = [
                        doctor.lower(),
                        doctor.replace('Dr. ', '').lower(),
                        doctor.split()[-1].lower()  # Last name only
                    ]
                    for variation in doctor_variations:
                        if variation in user_text:
                            appointment_data['doctor'] = doctor
                            break
                    if appointment_data.get('doctor'):
                        break
            
            # Extract date patterns
            if not appointment_data.get('date'):
                date_patterns = [
                    r"tomorrow",
                    r"today",
                    r"next week",
                    r"(\d{4}-\d{2}-\d{2})",
                    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                ]
                for pattern in date_patterns:
                    if re.search(pattern, user_text, re.IGNORECASE):
                        appointment_data['date'] = self._parse_date_from_text(user_text)
                        break
            
            # Extract time patterns
            if not appointment_data.get('time'):
                time_patterns = [
                    r"(\d{1,2}):(\d{2})\s*(am|pm)",
                    r"(\d{1,2})\s*(am|pm)",
                    r"(\d{1,2}):(\d{2})"
                ]
                for pattern in time_patterns:
                    match = re.search(pattern, user_text, re.IGNORECASE)
                    if match:
                        appointment_data['time'] = self._parse_time_from_match(match)
                        break
        
        # Check if we have minimum required information
        required_fields = ['patient_name', 'doctor', 'date', 'time']
        if all(appointment_data.get(field) for field in required_fields):
            return appointment_data
        
        return None

    def _parse_date_from_text(self, text: str) -> str:
        """Parse date from natural language text"""
        text = text.lower()
        today = datetime.now().date()
        
        if "tomorrow" in text:
            target_date = today + timedelta(days=1)
        elif "today" in text:
            target_date = today
        elif "next week" in text:
            target_date = today + timedelta(days=7)
        elif "monday" in text:
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "tuesday" in text:
            days_ahead = 1 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "wednesday" in text:
            days_ahead = 2 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "thursday" in text:
            days_ahead = 3 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "friday" in text:
            days_ahead = 4 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        else:
            # Default to tomorrow if no clear date found
            target_date = today + timedelta(days=1)
        
        return target_date.strftime('%Y-%m-%d')

    def _parse_time_from_match(self, match) -> str:
        """Parse time from regex match"""
        groups = match.groups()
        
        if len(groups) >= 3:  # Hour:Minute AM/PM
            hour = int(groups[0])
            minute = int(groups[1])
            period = groups[2].lower()
            
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
                
            return f"{hour:02d}:{minute:02d}"
        
        elif len(groups) >= 2 and groups[1] in ['am', 'pm']:  # Hour AM/PM
            hour = int(groups[0])
            period = groups[1].lower()
            
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
                
            return f"{hour:02d}:00"
        
        else:  # Just hour:minute in 24h format
            hour = int(groups[0])
            minute = int(groups[1]) if len(groups) > 1 else 0
            return f"{hour:02d}:{minute:02d}"

    async def _create_or_find_patient(self, appointment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create or find patient in MongoDB"""
        try:
            db = get_database()
            patient_name = appointment_data.get('patient_name')
            patient_phone = appointment_data.get('phone')
            
            if not patient_name:
                return None
            
            # Try to find existing patient by name
            name_parts = patient_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
                
                # Search for existing patient
                existing_patient = await db.patients.find_one({
                    "$and": [
                        {"first_name": {"$regex": f"^{first_name}$", "$options": "i"}},
                        {"last_name": {"$regex": f"^{last_name}$", "$options": "i"}},
                        {"is_active": True}
                    ]
                })
                
                if existing_patient:
                    logger.info(f"Found existing patient: {existing_patient['patient_id']}")
                    return existing_patient
            
            # Create new patient
            logger.info(f"Creating new patient: {patient_name}")
            
            patient_id = f"P{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
            
            new_patient = {
                "patient_id": patient_id,
                "first_name": name_parts[0] if name_parts else patient_name,
                "last_name": ' '.join(name_parts[1:]) if len(name_parts) > 1 else "",
                "phone": patient_phone,
                "email": None,
                "date_of_birth": None,
                "gender": None,
                "address": None,
                "city": None,
                "state": None,
                "zip_code": None,
                "emergency_contact_name": None,
                "emergency_contact_phone": None,
                "medical_history": [],
                "allergies": [],
                "medications": [],
                "insurance_provider": None,
                "insurance_id": None,
                "notes": f"Patient created via voice booking on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db.patients.insert_one(new_patient)
            new_patient["_id"] = result.inserted_id
            
            logger.info(f"Created new patient with ID: {patient_id}")
            return new_patient
            
        except Exception as e:
            logger.error(f"Error creating/finding patient: {e}")
            return None

    async def _create_appointment_from_voice(self, appointment_data: Dict[str, Any], patient: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create appointment in MongoDB from voice data"""
        try:
            db = get_database()
            
            # Parse date and time
            appointment_date_str = f"{appointment_data['date']} {appointment_data['time']}"
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d %H:%M')
            
            # Check if slot is available
            existing_appointment = await db.appointments.find_one({
                "doctor_name": appointment_data['doctor'],
                "appointment_date": appointment_date,
                "status": {"$nin": ["cancelled"]}
            })
            
            if existing_appointment:
                logger.warning(f"Time slot already booked: {appointment_date}")
                return None
            
            # Create appointment
            new_appointment = {
                "patient_id": patient["patient_id"],
                "patient_name": appointment_data["patient_name"],
                "patient_phone": appointment_data.get("phone") or patient.get("phone"),
                "patient_email": patient.get("email"),
                "doctor_name": appointment_data["doctor"],
                "appointment_date": appointment_date,
                "duration_minutes": 30,
                "status": "scheduled",
                "reason": appointment_data.get("reason", "General consultation"),
                "notes": f"Appointment booked via voice on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db.appointments.insert_one(new_appointment)
            new_appointment["_id"] = result.inserted_id
            
            logger.info(f"Created appointment: {result.inserted_id}")
            return new_appointment
            
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return None

    async def create_appointment(self, appointment_data: AppointmentCreate) -> AppointmentResponse:
        """Create a new appointment"""
        try:
            db = get_database()
            appointment = Appointment(**appointment_data.dict())
            result = await db[self.collection_name].insert_one(appointment.dict(by_alias=True))
            
            created_appointment = await db[self.collection_name].find_one({"_id": result.inserted_id})
            return AppointmentResponse(
                id=str(created_appointment["_id"]),
                **{k: v for k, v in created_appointment.items() if k != "_id"}
            )
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise

    async def get_appointment(self, appointment_id: str) -> Optional[AppointmentResponse]:
        """Get appointment by ID"""
        try:
            db = get_database()
            appointment = await db[self.collection_name].find_one({"_id": ObjectId(appointment_id)})
            
            if appointment:
                return AppointmentResponse(
                    id=str(appointment["_id"]),
                    **{k: v for k, v in appointment.items() if k != "_id"}
                )
            return None
        except Exception as e:
            logger.error(f"Error getting appointment: {e}")
            raise

    async def get_appointments_by_patient(self, patient_id: str) -> List[AppointmentResponse]:
        """Get all appointments for a patient"""
        try:
            db = get_database()
            cursor = db[self.collection_name].find({"patient_id": patient_id})
            appointments = await cursor.to_list(length=None)
            
            return [
                AppointmentResponse(
                    id=str(appointment["_id"]),
                    **{k: v for k, v in appointment.items() if k != "_id"}
                )
                for appointment in appointments
            ]
        except Exception as e:
            logger.error(f"Error getting patient appointments: {e}")
            raise

    async def get_appointments_by_doctor(self, doctor_name: str, date: Optional[datetime] = None) -> List[AppointmentResponse]:
        """Get appointments for a doctor, optionally filtered by date"""
        try:
            db = get_database()
            query = {"doctor_name": doctor_name}
            
            if date:
                start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)
                query["appointment_date"] = {
                    "$gte": start_of_day,
                    "$lt": end_of_day
                }
            
            cursor = db[self.collection_name].find(query)
            appointments = await cursor.to_list(length=None)
            
            return [
                AppointmentResponse(
                    id=str(appointment["_id"]),
                    **{k: v for k, v in appointment.items() if k != "_id"}
                )
                for appointment in appointments
            ]
        except Exception as e:
            logger.error(f"Error getting doctor appointments: {e}")
            raise

    async def update_appointment(self, appointment_id: str, update_data: AppointmentUpdate) -> Optional[AppointmentResponse]:
        """Update an appointment"""
        try:
            db = get_database()
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await db[self.collection_name].update_one(
                {"_id": ObjectId(appointment_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count:
                updated_appointment = await db[self.collection_name].find_one({"_id": ObjectId(appointment_id)})
                return AppointmentResponse(
                    id=str(updated_appointment["_id"]),
                    **{k: v for k, v in updated_appointment.items() if k != "_id"}
                )
            return None
        except Exception as e:
            logger.error(f"Error updating appointment: {e}")
            raise

    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Cancel an appointment"""
        try:
            update_data = AppointmentUpdate(status="cancelled")
            result = await self.update_appointment(appointment_id, update_data)
            return result is not None
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            raise

    async def get_available_slots(self, doctor_name: str, date: datetime) -> List[datetime]:
        """Get available time slots for a doctor on a specific date"""
        try:
            # Get existing appointments for the doctor on the date
            existing_appointments = await self.get_appointments_by_doctor(doctor_name, date)
            
            # Generate all possible slots (9 AM to 5 PM, 30-minute intervals)
            start_time = date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time = date.replace(hour=17, minute=0, second=0, microsecond=0)
            
            all_slots = []
            current_time = start_time
            while current_time < end_time:
                all_slots.append(current_time)
                current_time += timedelta(minutes=30)
            
            # Remove booked slots
            booked_slots = [apt.appointment_date for apt in existing_appointments if apt.status != "cancelled"]
            available_slots = [slot for slot in all_slots if slot not in booked_slots]
            
            return available_slots
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            raise

    async def search_appointments(self, query: str = "", filters: Dict[str, Any] = None) -> List[AppointmentResponse]:
        """Search appointments with text query and filters"""
        try:
            db = get_database()
            
            # Build MongoDB query
            mongo_query = {}
            
            # Text search
            if query:
                mongo_query["$or"] = [
                    {"patient_name": {"$regex": query, "$options": "i"}},
                    {"doctor_name": {"$regex": query, "$options": "i"}},
                    {"reason": {"$regex": query, "$options": "i"}}
                ]
            
            # Apply filters
            if filters:
                if filters.get('status'):
                    mongo_query['status'] = filters['status']
                if filters.get('doctor'):
                    mongo_query['doctor_name'] = filters['doctor']
                if filters.get('date_from'):
                    mongo_query['appointment_date'] = {"$gte": filters['date_from']}
                if filters.get('date_to'):
                    if 'appointment_date' not in mongo_query:
                        mongo_query['appointment_date'] = {}
                    mongo_query['appointment_date']['$lte'] = filters['date_to']
                if filters.get('patient_id'):
                    mongo_query['patient_id'] = filters['patient_id']
            
            cursor = db[self.collection_name].find(mongo_query).sort("appointment_date", 1)
            appointments = await cursor.to_list(length=100)  # Limit to 100 results
            
            return [
                AppointmentResponse(
                    id=str(appointment["_id"]),
                    **{k: v for k, v in appointment.items() if k != "_id"}
                )
                for appointment in appointments
            ]
            
        except Exception as e:
            logger.error(f"Error searching appointments: {e}")
            return []

    async def get_appointment_statistics(self) -> Dict[str, Any]:
        """Get appointment statistics for dashboard"""
        try:
            db = get_database()
            
            # Get current date range
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            # Run aggregation pipelines
            stats = {}
            
            # Today's appointments
            stats['today'] = await db[self.collection_name].count_documents({
                "appointment_date": {"$gte": today, "$lt": tomorrow},
                "status": {"$nin": ["cancelled"]}
            })
            
            # This week's appointments
            stats['this_week'] = await db[self.collection_name].count_documents({
                "appointment_date": {"$gte": week_start},
                "status": {"$nin": ["cancelled"]}
            })
            
            # This month's appointments
            stats['this_month'] = await db[self.collection_name].count_documents({
                "appointment_date": {"$gte": month_start},
                "status": {"$nin": ["cancelled"]}
            })
            
            # Status distribution
            status_pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            status_results = await db[self.collection_name].aggregate(status_pipeline).to_list(length=None)
            stats['by_status'] = {item['_id']: item['count'] for item in status_results}
            
            # Doctor distribution
            doctor_pipeline = [
                {"$group": {"_id": "$doctor_name", "count": {"$sum": 1}}}
            ]
            doctor_results = await db[self.collection_name].aggregate(doctor_pipeline).to_list(length=None)
            stats['by_doctor'] = {item['_id']: item['count'] for item in doctor_results}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting appointment statistics: {e}")
            return {}

    async def get_doctor_appointment_statistics(self, doctor_name: str) -> Dict[str, Any]:
        """Get appointment statistics for a specific doctor"""
        try:
            db = get_database()
            
            # Get current date range
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            # Base query for this doctor
            base_query = {"doctor_name": doctor_name}
            
            stats = {}
            
            # Today's appointments
            stats['today'] = await db[self.collection_name].count_documents({
                **base_query,
                "appointment_date": {"$gte": today, "$lt": tomorrow},
                "status": {"$nin": ["cancelled"]}
            })
            
            # This week's appointments
            stats['this_week'] = await db[self.collection_name].count_documents({
                **base_query,
                "appointment_date": {"$gte": week_start},
                "status": {"$nin": ["cancelled"]}
            })
            
            # This month's appointments
            stats['this_month'] = await db[self.collection_name].count_documents({
                **base_query,
                "appointment_date": {"$gte": month_start},
                "status": {"$nin": ["cancelled"]}
            })
            
            # Status distribution for this doctor
            status_pipeline = [
                {"$match": base_query},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            status_results = await db[self.collection_name].aggregate(status_pipeline).to_list(length=None)
            stats['by_status'] = {item['_id']: item['count'] for item in status_results}
            
            # Total appointments for this doctor
            stats['total_appointments'] = await db[self.collection_name].count_documents(base_query)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting doctor appointment statistics: {e}")
            return {}

    async def get_patient_appointment_statistics(self, patient_id: str) -> Dict[str, Any]:
        """Get appointment statistics for a specific patient"""
        try:
            db = get_database()
            
            # Get current date range
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            # Base query for this patient
            base_query = {"patient_id": patient_id}
            
            stats = {}
            
            # Today's appointments
            stats['today'] = await db[self.collection_name].count_documents({
                **base_query,
                "appointment_date": {"$gte": today, "$lt": tomorrow},
                "status": {"$nin": ["cancelled"]}
            })
            
            # This week's appointments
            stats['this_week'] = await db[self.collection_name].count_documents({
                **base_query,
                "appointment_date": {"$gte": week_start},
                "status": {"$nin": ["cancelled"]}
            })
            
            # This month's appointments
            stats['this_month'] = await db[self.collection_name].count_documents({
                **base_query,
                "appointment_date": {"$gte": month_start},
                "status": {"$nin": ["cancelled"]}
            })
            
            # Status distribution for this patient
            status_pipeline = [
                {"$match": base_query},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            status_results = await db[self.collection_name].aggregate(status_pipeline).to_list(length=None)
            stats['by_status'] = {item['_id']: item['count'] for item in status_results}
            
            # Total appointments for this patient
            stats['total_appointments'] = await db[self.collection_name].count_documents(base_query)
            
            # Upcoming appointments
            stats['upcoming'] = await db[self.collection_name].count_documents({
                **base_query,
                "appointment_date": {"$gte": today},
                "status": {"$nin": ["cancelled", "completed"]}
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting patient appointment statistics: {e}")
            return {}

    def validate_appointment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate appointment data from voice input"""
        errors = []
        suggestions = []
        
        # Validate patient name
        if not data.get('patient_name') or len(data['patient_name'].strip()) < 2:
            errors.append("Patient name is required")
            suggestions.append("Please provide the patient's full name")
        
        # Validate date
        if data.get('date'):
            try:
                apt_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                if apt_date < datetime.now().date():
                    errors.append("Appointment date cannot be in the past")
                    suggestions.append("Please choose a future date")
                elif apt_date.strftime('%A').lower() not in self.business_hours['days']:
                    errors.append("Appointments are only available on weekdays")
                    suggestions.append("Please choose Monday through Friday")
            except ValueError:
                errors.append("Invalid date format")
                suggestions.append("Please use format YYYY-MM-DD")
        else:
            errors.append("Appointment date is required")
            suggestions.append("Please specify when you'd like the appointment")
        
        # Validate time
        if data.get('time'):
            try:
                apt_time = datetime.strptime(data['time'], '%H:%M').time()
                if apt_time.hour < self.business_hours['start'] or apt_time.hour >= self.business_hours['end']:
                    errors.append(f"Appointments are only available from {self.business_hours['start']}:00 AM to {self.business_hours['end']}:00 PM")
                    suggestions.append(f"Please choose a time between {self.business_hours['start']}:00 AM and {self.business_hours['end']-1}:30 PM")
            except ValueError:
                errors.append("Invalid time format")
                suggestions.append("Please use format HH:MM (24-hour)")
        else:
            errors.append("Appointment time is required")
            suggestions.append("Please specify what time you prefer")
        
        # Validate doctor
        if data.get('doctor') and data['doctor'] not in self.available_doctors:
            errors.append("Doctor not available")
            suggestions.append(f"Available doctors: {', '.join(self.available_doctors)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'suggestions': suggestions
        }

appointment_service = AppointmentService()