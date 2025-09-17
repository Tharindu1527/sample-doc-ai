import asyncio
import json
import base64
from datetime import datetime, timedelta, time, date
from typing import AsyncGenerator, Dict, Any, Optional, List
import google.generativeai as genai
from deepgram import Deepgram

# Enhanced ElevenLabs import handling with multiple fallbacks
ELEVENLABS_AVAILABLE = False
generate = None
set_api_key = None
ElevenLabs = None

try:
    from elevenlabs import generate, set_api_key
    ELEVENLABS_AVAILABLE = True
    print("✓ ElevenLabs classic API loaded")
except ImportError:
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import play, stream, save
        ELEVENLABS_AVAILABLE = True
        generate = None
        set_api_key = None
        print("✓ ElevenLabs new API loaded")
    except ImportError:
        print("⚠️  ElevenLabs not available. Text-to-speech will be disabled.")
        ELEVENLABS_AVAILABLE = False

from config import settings
from database.mongodb import get_database
from api.patients import patient_service
from api.doctors import doctor_service
from services.appointment_service import appointment_service
import logging
import re

logger = logging.getLogger(__name__)

# Configure APIs
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
else:
    logger.warning("Gemini API key not provided")

if ELEVENLABS_AVAILABLE and set_api_key and settings.elevenlabs_api_key:
    set_api_key(settings.elevenlabs_api_key)

def serialize_datetime(obj):
    """Convert datetime objects to ISO string format"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.strftime("%H:%M:%S")
    return obj

def serialize_pydantic_model(model):
    """Convert Pydantic model to JSON-serializable dict"""
    if hasattr(model, 'dict'):
        data = model.dict()
        # Convert datetime objects to strings
        for key, value in data.items():
            if isinstance(value, (datetime, date, time)):
                data[key] = serialize_datetime(value)
            elif isinstance(value, list):
                data[key] = [serialize_datetime(item) if isinstance(item, (datetime, date, time)) else item for item in value]
        return data
    return model

def make_json_serializable(data):
    """Recursively make data JSON serializable"""
    if isinstance(data, dict):
        return {key: make_json_serializable(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [make_json_serializable(item) for item in data]
    elif isinstance(data, (datetime, date, time)):
        return serialize_datetime(data)
    elif hasattr(data, 'dict'):  # Pydantic model
        return make_json_serializable(serialize_pydantic_model(data))
    else:
        return data

class EnhancedVoiceService:
    def __init__(self):
        # Initialize Deepgram
        if settings.deepgram_api_key:
            self.deepgram = Deepgram(settings.deepgram_api_key)
        else:
            logger.warning("Deepgram API key not provided")
            self.deepgram = None
        
        # Initialize Gemini
        if settings.gemini_api_key:
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            logger.warning("Gemini API key not provided")
            self.gemini_model = None
        
        # Initialize ElevenLabs client for new API
        self.elevenlabs_client = None
        if ELEVENLABS_AVAILABLE and not generate and settings.elevenlabs_api_key:
            try:
                self.elevenlabs_client = ElevenLabs(api_key=settings.elevenlabs_api_key)
                print("✓ ElevenLabs client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize ElevenLabs client: {e}")
        
        self.conversation_context = []

    async def get_real_doctors_data(self) -> List[Dict[str, Any]]:
        """Fetch real doctors data from database with proper JSON serialization"""
        try:
            doctors = await doctor_service.get_available_doctors()
            doctor_data = []
            
            for doctor in doctors:
                # Convert working hours to serializable format
                working_hours = []
                if doctor.working_hours:
                    for wh in doctor.working_hours:
                        if hasattr(wh, 'dict'):
                            wh_dict = wh.dict()
                            # Convert time objects to strings
                            if 'start_time' in wh_dict and isinstance(wh_dict['start_time'], time):
                                wh_dict['start_time'] = wh_dict['start_time'].strftime("%H:%M:%S")
                            if 'end_time' in wh_dict and isinstance(wh_dict['end_time'], time):
                                wh_dict['end_time'] = wh_dict['end_time'].strftime("%H:%M:%S")
                            working_hours.append(wh_dict)
                        else:
                            # Handle if it's already a dict
                            working_hours.append(make_json_serializable(wh))
                
                doctor_info = {
                    'id': doctor.doctor_id,
                    'name': f"Dr. {doctor.first_name} {doctor.last_name}",
                    'first_name': doctor.first_name,
                    'last_name': doctor.last_name,
                    'specialty': doctor.specialty,
                    'department': doctor.department or 'General',
                    'years_experience': doctor.years_experience or 0,
                    'is_available': doctor.is_available,
                    'is_active': doctor.is_active,
                    'working_hours': working_hours,
                    'consultation_fee': float(doctor.consultation_fee) if doctor.consultation_fee else None,
                    'email': doctor.email,
                    'phone': doctor.phone,
                    'rating': float(doctor.rating) if doctor.rating else None,
                    'total_reviews': doctor.total_reviews or 0
                }
                doctor_data.append(doctor_info)
            
            return doctor_data
        except Exception as e:
            logger.error(f"Error fetching doctors data: {e}")
            return []

    async def get_real_patients_data(self, search_query: str = None) -> List[Dict[str, Any]]:
        """Fetch real patients data from database with proper JSON serialization"""
        try:
            if search_query:
                patients = await patient_service.search_patients(query=search_query)
            else:
                patients = await patient_service.get_all_patients(limit=50)
            
            patient_data = []
            for patient in patients:
                patient_info = {
                    'id': patient.patient_id,
                    'name': f"{patient.first_name} {patient.last_name}",
                    'first_name': patient.first_name,
                    'last_name': patient.last_name,
                    'phone': patient.phone,
                    'email': patient.email,
                    'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                    'gender': patient.gender,
                    'city': patient.city,
                    'state': patient.state,
                    'is_active': patient.is_active
                }
                patient_data.append(patient_info)
            
            return patient_data
        except Exception as e:
            logger.error(f"Error fetching patients data: {e}")
            return []

    async def get_available_slots_for_doctor(self, doctor_name: str, date: datetime) -> List[str]:
        """Get real available slots for a specific doctor"""
        try:
            # Clean doctor name
            clean_name = doctor_name.replace("Dr.", "").replace("Doctor", "").strip()
            
            # Find doctor by name
            doctor = await doctor_service.get_doctor_by_name(clean_name)
            if not doctor:
                return []
            
            # Get available slots
            slots = await appointment_service.get_available_slots(
                f"Dr. {doctor.first_name} {doctor.last_name}", 
                date
            )
            
            return [slot.strftime("%H:%M") for slot in slots]
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []

    async def find_patient_by_voice_info(self, patient_info: str) -> Optional[Dict[str, Any]]:
        """Find patient by name or phone from voice input"""
        try:
            # Try to extract phone number
            phone_pattern = r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\d{10})'
            phone_match = re.search(phone_pattern, patient_info)
            
            if phone_match:
                phone = phone_match.group(1)
                patient = await patient_service.get_patient_by_name_phone(phone=phone)
            else:
                # Search by name
                patient = await patient_service.get_patient_by_name_phone(name=patient_info)
            
            if patient:
                return {
                    'id': patient.patient_id,
                    'name': f"{patient.first_name} {patient.last_name}",
                    'first_name': patient.first_name,
                    'last_name': patient.last_name,
                    'phone': patient.phone,
                    'email': patient.email
                }
            return None
        except Exception as e:
            logger.error(f"Error finding patient: {e}")
            return None

    async def get_real_appointment_data(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Fetch real appointments data from database with proper JSON serialization"""
        try:
            if filters:
                appointments = await appointment_service.search_appointments(filters=filters)
            else:
                # Get recent appointments
                db = get_database()
                cursor = db["appointments"].find({}).sort("appointment_date", -1).limit(20)
                appointments_data = await cursor.to_list(length=20)
                
                appointments = []
                for apt in appointments_data:
                    appointment_info = {
                        'id': str(apt["_id"]),
                        'patient_id': apt.get('patient_id'),
                        'patient_name': apt.get('patient_name'),
                        'patient_phone': apt.get('patient_phone'),
                        'doctor_name': apt.get('doctor_name'),
                        'appointment_date': apt.get('appointment_date').isoformat() if apt.get('appointment_date') else None,
                        'status': apt.get('status'),
                        'reason': apt.get('reason'),
                        'duration_minutes': apt.get('duration_minutes', 30),
                        'created_at': apt.get('created_at').isoformat() if apt.get('created_at') else None
                    }
                    appointments.append(appointment_info)
                
                return appointments
            
            # Handle case where appointments is a list of Pydantic models
            appointment_data = []
            for apt in appointments:
                if hasattr(apt, 'dict'):
                    apt_dict = make_json_serializable(apt.dict())
                    appointment_data.append(apt_dict)
                else:
                    appointment_data.append(make_json_serializable(apt))
            
            return appointment_data
            
        except Exception as e:
            logger.error(f"Error fetching appointments: {e}")
            return []

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using Deepgram with enhanced error handling"""
        if not self.deepgram:
            raise Exception("Deepgram not initialized - check API key")
        
        try:
            response = await self.deepgram.transcription.prerecorded(
                {'buffer': audio_data, 'mimetype': 'audio/wav'},
                {
                    'punctuate': True, 
                    'language': 'en',
                    'model': settings.deepgram_model,
                    'smart_format': True,
                    'diarize': False
                }
            )
            
            if response['results']['channels'][0]['alternatives']:
                transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
                confidence = response['results']['channels'][0]['alternatives'][0]['confidence']
                logger.info(f"Transcription confidence: {confidence}")
                logger.info(f"Transcribed: {transcript}")
                return transcript
            return ""
            
        except Exception as e:
            logger.error(f"Deepgram transcription error: {str(e)}")
            raise Exception(f"Speech recognition failed: {str(e)}")

    async def generate_response(self, transcript: str) -> Dict[str, Any]:
        """Generate AI response using Gemini with real database context"""
        if not self.gemini_model:
            raise Exception("Gemini not initialized - check API key")
        
        try:
            # Get real data from database
            doctors_data = await self.get_real_doctors_data()
            recent_appointments = await self.get_real_appointment_data()
            
            # Add conversation context
            context = "\n".join([f"User: {item['user']}\nAI: {item['ai']}" for item in self.conversation_context[-3:]])
            
            current_time = datetime.now()
            
            # Format doctors information (using only serializable data)
            doctors_list = []
            for doctor in doctors_data:
                working_today = "Available today" if doctor['is_available'] else "Not available today"
                doctors_list.append(f"- {doctor['name']} ({doctor['specialty']}, {doctor['department']}) - {working_today}")
            
            doctors_info = "\n".join(doctors_list) if doctors_list else "No doctors currently available"
            
            # Format recent appointments for context
            recent_appointments_info = ""
            if recent_appointments:
                recent_appointments_info = "Recent appointments:\n"
                for apt in recent_appointments[:5]:
                    apt_date_str = apt['appointment_date']
                    if apt_date_str:
                        try:
                            if isinstance(apt_date_str, str):
                                apt_date = datetime.fromisoformat(apt_date_str.replace('Z', '+00:00'))
                            else:
                                apt_date = apt_date_str
                            recent_appointments_info += f"- {apt['patient_name']} with {apt['doctor_name']} on {apt_date.strftime('%Y-%m-%d %H:%M')} ({apt['status']})\n"
                        except:
                            recent_appointments_info += f"- {apt['patient_name']} with {apt['doctor_name']} ({apt['status']})\n"

            prompt = f"""You are DocTalk AI, a professional medical appointment assistant for a healthcare clinic.

Current time: {current_time.strftime('%Y-%m-%d %H:%M')}

AVAILABLE DOCTORS (REAL DATA FROM DATABASE):
{doctors_info}

{recent_appointments_info}

Previous conversation:
{context}

Current user message: {transcript}

IMPORTANT INSTRUCTIONS:
1. Use ONLY the real doctors listed above - never suggest fictional doctors
2. For appointment booking, collect: patient name, preferred date/time, reason for visit, doctor preference
3. When suggesting doctors, use the actual names and specialties from the database
4. If no doctors are available for a specialty, explain this clearly
5. Be professional, empathetic, and helpful
6. Keep responses conversational but informative (under 150 words)
7. For urgent medical concerns, suggest contacting emergency services
8. Validate appointment details before confirming only one time is enough
9. If a requested doctor is not available, suggest alternative doctors from the list

Respond professionally and helpfully using the real clinic data."""

            response = self.gemini_model.generate_content(prompt)
            ai_response = response.text.strip()
            
            # Update conversation context
            self.conversation_context.append({
                'user': transcript,
                'ai': ai_response,
                'timestamp': datetime.now().isoformat()
            })
            
            # Keep only last 5 exchanges
            self.conversation_context = self.conversation_context[-5:]
            
            # Extract intent and entities with real data context
            intent_data = await self.extract_intent_with_real_data(transcript, ai_response, doctors_data)
            
            # Return JSON-serializable data
            result = {
                'response': ai_response,
                'intent': intent_data.get('intent', 'general'),
                'entities': intent_data.get('entities', {}),
                'confidence': intent_data.get('confidence', 0.5),
                'suggestions': intent_data.get('suggestions', []),
                'urgency': intent_data.get('urgency', 'low'),
                'available_doctors': doctors_data,  # Already JSON-serializable
                'recent_appointments': recent_appointments[:3]  # Already JSON-serializable
            }
            
            return make_json_serializable(result)
            
        except Exception as e:
            logger.error(f"Gemini response error: {str(e)}")
            raise Exception(f"AI response generation failed: {str(e)}")

    async def extract_intent_with_real_data(self, user_text: str, ai_response: str = "", doctors_data: List[Dict] = None) -> Dict[str, Any]:
        """Extract intent and entities with real database context"""
        if not self.gemini_model:
            return {
                'intent': 'general',
                'entities': {},
                'confidence': 0.3,
                'suggestions': [],
                'urgency': 'low'
            }
        
        try:
            # Get current doctors list for validation
            if not doctors_data:
                doctors_data = await self.get_real_doctors_data()
            
            doctors_list = [f"{doc['name']} ({doc['specialty']})" for doc in doctors_data]
            
            intent_prompt = f"""
            Analyze this conversation for medical appointment management:
            
            User: "{user_text}"
            AI Response: "{ai_response}"
            
            AVAILABLE DOCTORS IN DATABASE:
            {chr(10).join(doctors_list)}
            
            Return JSON with:
            {{
                "intent": "book_appointment" | "cancel_appointment" | "reschedule_appointment" | "check_availability" | "inquiry" | "emergency" | "general",
                "entities": {{
                    "patient_name": "extracted name or null",
                    "date": "YYYY-MM-DD or null", 
                    "time": "HH:MM or null",
                    "doctor": "exact doctor name from available list or null",
                    "specialty": "medical specialty or null",
                    "reason": "medical reason or null",
                    "phone": "phone number or null"
                }},
                "confidence": 0.0-1.0,
                "suggestions": ["list of helpful suggestions based on available doctors"],
                "urgency": "low" | "medium" | "high" | "emergency"
            }}
            
            IMPORTANT: Only use doctor names that exist in the available doctors list above.
            Only return valid JSON, nothing else.
            """
            
            response = self.gemini_model.generate_content(intent_prompt)
            response_text = response.text.strip()
            
            # Clean the response to ensure it's valid JSON
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Try to parse JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}, Response: {response_text}")
                # Return a safe default
                result = {
                    'intent': 'general',
                    'entities': {},
                    'confidence': 0.3,
                    'suggestions': [f"Available doctors: {', '.join([doc['name'] for doc in doctors_data[:3]])}"],
                    'urgency': 'low'
                }
            
            # Validate and enrich entities with real data
            if result.get('entities'):
                entities = result['entities']
                
                # Validate date format
                if entities.get('date'):
                    try:
                        datetime.strptime(entities['date'], '%Y-%m-%d')
                    except ValueError:
                        entities['date'] = None
                
                # Validate doctor name against real database
                if entities.get('doctor'):
                    doctor_found = False
                    for doc in doctors_data:
                        if entities['doctor'].lower() in doc['name'].lower() or doc['name'].lower() in entities['doctor'].lower():
                            entities['doctor'] = doc['name']  # Use exact name from database
                            entities['doctor_id'] = doc['id']
                            entities['doctor_specialty'] = doc['specialty']
                            doctor_found = True
                            break
                    
                    if not doctor_found:
                        entities['doctor'] = None
                        # Add suggestion for available doctors
                        if not result.get('suggestions'):
                            result['suggestions'] = []
                        result['suggestions'].append(f"Available doctors: {', '.join([doc['name'] for doc in doctors_data[:5]])}")
                
                # If specialty mentioned but no specific doctor, suggest doctors
                if entities.get('specialty') and not entities.get('doctor'):
                    matching_doctors = [doc for doc in doctors_data if entities['specialty'].lower() in doc['specialty'].lower()]
                    if matching_doctors:
                        if not result.get('suggestions'):
                            result['suggestions'] = []
                        result['suggestions'].append(f"Doctors for {entities['specialty']}: {', '.join([doc['name'] for doc in matching_doctors[:3]])}")
            
            return make_json_serializable(result)
            
        except Exception as e:
            logger.error(f"Intent extraction error: {str(e)}")
            # Fallback with real doctor suggestions
            doctors_data = doctors_data or await self.get_real_doctors_data()
            return {
                'intent': 'general', 
                'entities': {}, 
                'confidence': 0.3,
                'suggestions': [f"Available doctors: {', '.join([doc['name'] for doc in doctors_data[:3]])}"] if doctors_data else [],
                'urgency': 'low'
            }

    async def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech with enhanced fallback handling"""
        if not ELEVENLABS_AVAILABLE:
            logger.warning("ElevenLabs not available, returning empty audio")
            return b""
        
        if not settings.elevenlabs_api_key:
            logger.warning("ElevenLabs API key not provided, returning empty audio")
            return b""
        
        try:
            # Clean text for better speech synthesis
            clean_text = self._clean_text_for_speech(text)
            
            if generate:
                # Classic API
                audio = generate(
                    text=clean_text,
                    voice=settings.elevenlabs_voice_id,
                    model="eleven_monolingual_v1"
                )
                return audio if isinstance(audio, bytes) else b""
            elif self.elevenlabs_client:
                # New API
                try:
                    audio = self.elevenlabs_client.generate(
                        text=clean_text,
                        voice=settings.elevenlabs_voice_id,
                        model="eleven_monolingual_v1"
                    )
                    return audio if isinstance(audio, bytes) else b""
                except Exception as e:
                    logger.error(f"ElevenLabs new API error: {e}")
                    return b""
            else:
                logger.warning("No ElevenLabs method available")
                return b""
                
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {str(e)}")
            return b""
    
    def _clean_text_for_speech(self, text: str) -> str:
        """Clean text for better speech synthesis"""
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        
        # Handle common medical abbreviations
        replacements = {
            'Dr.': 'Doctor',
            'appt': 'appointment',
            'w/': 'with',
            'b/c': 'because',
            'etc.': 'etcetera'
        }
        
        for abbrev, full in replacements.items():
            text = text.replace(abbrev, full)
        
        return text

    async def process_voice_input(self, audio_data: bytes) -> Dict[str, Any]:
        """Complete voice processing pipeline with real database integration and JSON serialization"""
        try:
            # Handle empty audio
            if not audio_data or len(audio_data) == 0:
                return {
                    'transcript': '',
                    'response': 'I couldn\'t hear you clearly. Could you please speak a bit louder or closer to the microphone?',
                    'audio': None,
                    'intent': 'general',
                    'entities': {},
                    'suggestions': ['Try speaking more clearly', 'Check your microphone'],
                    'urgency': 'low'
                }
            
            # Transcribe
            transcript = await self.transcribe_audio(audio_data)
            if not transcript.strip():
                return {
                    'transcript': '',
                    'response': 'I couldn\'t understand what you said. Please try speaking more clearly.',
                    'audio': None,
                    'intent': 'general',
                    'entities': {},
                    'suggestions': ['Speak more clearly', 'Check microphone volume'],
                    'urgency': 'low'
                }
            
            logger.info(f"Transcribed: {transcript}")
            
            # Generate AI response with real database context
            ai_data = await self.generate_response(transcript)
            
            # Generate speech
            audio_b64 = None
            try:
                audio = await self.text_to_speech(ai_data['response'])
                if audio:
                    audio_b64 = base64.b64encode(audio).decode('utf-8')
            except Exception as tts_error:
                logger.error(f"TTS failed: {tts_error}")
                audio_b64 = None
            
            result = {
                'transcript': transcript,
                'response': ai_data['response'],
                'audio': audio_b64,
                'intent': ai_data['intent'],
                'entities': ai_data['entities'],
                'confidence': ai_data['confidence'],
                'suggestions': ai_data.get('suggestions', []),
                'urgency': ai_data.get('urgency', 'low'),
                'available_doctors': ai_data.get('available_doctors', []),
                'recent_appointments': ai_data.get('recent_appointments', [])
            }
            
            return make_json_serializable(result)
            
        except Exception as e:
            logger.error(f"Voice processing error: {str(e)}")
            error_response = 'I\'m sorry, I\'m experiencing technical difficulties. Please try again in a moment or contact our office directly.'
            
            try:
                error_audio = await self.text_to_speech(error_response)
                error_audio_b64 = base64.b64encode(error_audio).decode('utf-8') if error_audio else None
            except:
                error_audio_b64 = None
            
            return {
                'transcript': '',
                'response': error_response,
                'audio': error_audio_b64,
                'intent': 'error',
                'entities': {},
                'error': str(e),
                'suggestions': ['Try again', 'Contact office directly', 'Check internet connection'],
                'urgency': 'low'
            }

    async def process_audio_stream(self, audio_data: bytes) -> Dict[str, Any]:
        """Process incoming audio stream through the voice pipeline with JSON serialization"""
        result = await self.process_voice_input(audio_data)
        
        response = {
            "transcript": result['transcript'],
            "ai_response": {
                "text": result['response'],
                "intent": result['intent'],
                "extracted_info": result['entities']
            },
            "audio_response": result['audio'],
            "timestamp": datetime.utcnow().isoformat(),
            "suggestions": result.get('suggestions', []),
            "urgency": result.get('urgency', 'low'),
            "available_doctors": result.get('available_doctors', []),
            "recent_appointments": result.get('recent_appointments', [])
        }
        
        return make_json_serializable(response)

    def reset_conversation(self):
        """Reset conversation context"""
        self.conversation_context = []
        logger.info("Conversation context reset")
    
    def get_conversation_history(self) -> list:
        """Get current conversation history"""
        return self.conversation_context.copy()

    def health_check(self) -> Dict[str, Any]:
        """Check health of all voice service components"""
        health = {
            "deepgram": "unavailable",
            "gemini": "unavailable", 
            "elevenlabs": "unavailable",
            "database": "unavailable"
        }
        
        if self.deepgram and settings.deepgram_api_key:
            health["deepgram"] = "available"
        
        if self.gemini_model and settings.gemini_api_key:
            health["gemini"] = "available"
            
        if ELEVENLABS_AVAILABLE and settings.elevenlabs_api_key:
            health["elevenlabs"] = "available"
        
        try:
            # Test database connection
            from database.mongodb import health_check
            import asyncio
            loop = asyncio.get_event_loop()
            db_healthy = loop.run_until_complete(health_check())
            if db_healthy:
                health["database"] = "available"
        except:
            pass
        
        return health

# Global instance
voice_service = EnhancedVoiceService()