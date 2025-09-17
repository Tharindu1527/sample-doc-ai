import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from services.voice_service import voice_service
from services.appointment_service import appointment_service
from api.patients import patient_service
from api.doctors import doctor_service
from models.appointment import AppointmentCreate
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/process")
async def process_audio(audio_file: UploadFile = File(...)):
    """Process uploaded audio file through the enhanced voice pipeline with real database data"""
    try:
        # Validate file type
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="Invalid audio file type")
        
        # Read audio file
        audio_data = await audio_file.read()
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Process through enhanced voice pipeline with real database integration
        result = await voice_service.process_voice_input(audio_data)
        
        # Handle appointment actions if intent detected
        if result.get('intent') in ['book_appointment', 'cancel_appointment', 'reschedule_appointment']:
            appointment_result = await handle_appointment_action_with_real_data(result)
            result['appointment_action'] = appointment_result
        
        return {
            'success': True,
            'data': result,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(e)}")

async def handle_appointment_action_with_real_data(voice_result: dict) -> dict:
    """Handle appointment-related actions using real database data"""
    try:
        intent = voice_result.get('intent')
        entities = voice_result.get('entities', {})
        
        if intent == 'book_appointment':
            return await handle_booking_with_real_data(entities)
        elif intent == 'cancel_appointment':
            return await handle_cancellation_with_real_data(entities)
        elif intent == 'reschedule_appointment':
            return await handle_reschedule_with_real_data(entities)
        
        return {
            'action': 'no_action',
            'message': 'No specific appointment action required.'
        }
        
    except Exception as e:
        logger.error(f"Error handling appointment action: {e}")
        return {
            'action': 'error',
            'message': 'Sorry, there was an error processing your appointment request.',
            'error': str(e)
        }

async def handle_booking_with_real_data(entities: dict) -> dict:
    """Handle appointment booking with real database validation"""
    try:
        # Extract information
        patient_name = entities.get("patient_name")
        doctor_name = entities.get("doctor")
        doctor_id = entities.get("doctor_id")
        date_str = entities.get("date")
        time_str = entities.get("time")
        reason = entities.get("reason", "General consultation")
        
        # Validate required fields
        missing_fields = []
        if not patient_name:
            missing_fields.append("patient_name")
        if not doctor_name and not doctor_id:
            missing_fields.append("doctor")
        if not date_str:
            missing_fields.append("date")
        if not time_str:
            missing_fields.append("time")
        
        if missing_fields:
            # Get available doctors for suggestions
            doctors = await voice_service.get_real_doctors_data()
            doctor_suggestions = [doc['name'] for doc in doctors[:5]]
            
            return {
                'action': 'validation_failed',
                'errors': missing_fields,
                'message': f'Please provide: {", ".join(missing_fields)}',
                'suggestions': {
                    'available_doctors': doctor_suggestions,
                    'example': 'Try saying: "Book appointment for John Doe with Dr. Smith tomorrow at 2 PM"'
                }
            }
        
        # Validate doctor exists
        if doctor_name and not doctor_id:
            doctor = await doctor_service.get_doctor_by_name(doctor_name.replace("Dr.", "").strip())
            if not doctor:
                # Get available doctors for suggestions
                doctors = await voice_service.get_real_doctors_data()
                available_doctors = [doc['name'] for doc in doctors if doc['is_available']]
                
                return {
                    'action': 'doctor_not_found',
                    'message': f'Doctor "{doctor_name}" is not available.',
                    'suggestions': {
                        'available_doctors': available_doctors,
                        'message': 'Here are our available doctors:'
                    }
                }
            
            doctor_name = f"Dr. {doctor.first_name} {doctor.last_name}"
            doctor_id = doctor.doctor_id
        
        # Parse date and time
        try:
            if "tomorrow" in date_str.lower():
                appointment_date = datetime.now() + timedelta(days=1)
            elif "today" in date_str.lower():
                appointment_date = datetime.now()
            else:
                appointment_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Parse time
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            appointment_date = appointment_date.replace(
                hour=time_obj.hour,
                minute=time_obj.minute,
                second=0,
                microsecond=0
            )
            
        except ValueError as e:
            return {
                'action': 'invalid_datetime',
                'message': f'Invalid date or time format: {e}',
                'suggestions': {
                    'example': 'Try: "tomorrow at 2 PM" or "2024-12-25 at 14:30"'
                }
            }
        
        # Check if appointment is in the past
        if appointment_date <= datetime.now():
            return {
                'action': 'invalid_datetime',
                'message': 'Cannot book appointments in the past.',
                'suggestions': {
                    'message': 'Please choose a future date and time.'
                }
            }
        
        # Check availability
        available_slots = await voice_service.get_available_slots_for_doctor(doctor_name, appointment_date)
        requested_time = appointment_date.strftime("%H:%M")
        
        if requested_time not in available_slots:
            return {
                'action': 'slot_unavailable',
                'message': f'The requested time slot ({requested_time}) is not available for {doctor_name}.',
                'suggestions': {
                    'available_slots': available_slots[:10],  # Show next 10 available slots
                    'date': appointment_date.strftime("%Y-%m-%d"),
                    'doctor': doctor_name
                }
            }
        
        # Find or validate patient
        patient = None
        if patient_name:
            patient = await voice_service.find_patient_by_voice_info(patient_name)
        
        if not patient:
            # Create a temporary patient ID for the appointment
            patient_id = f"TEMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            patient_phone = entities.get('phone', '')
            patient_email = entities.get('email', '')
            
            return {
                'action': 'patient_not_found',
                'message': f'Patient "{patient_name}" not found in our system.',
                'suggestions': {
                    'message': 'We can still book the appointment. Please provide a phone number.',
                    'next_step': 'create_appointment_with_new_patient',
                    'appointment_details': {
                        'patient_name': patient_name,
                        'doctor_name': doctor_name,
                        'date_time': appointment_date.isoformat(),
                        'reason': reason
                    }
                }
            }
        
        # Create appointment with validated data
        appointment_data = AppointmentCreate(
            patient_id=patient['id'],
            patient_name=patient['name'],
            patient_phone=patient.get('phone', ''),
            patient_email=patient.get('email', ''),
            doctor_name=doctor_name,
            appointment_date=appointment_date,
            duration_minutes=30,
            status="scheduled",
            reason=reason
        )
        
        result = await appointment_service.create_appointment(appointment_data)
        
        return {
            'action': 'appointment_created',
            'message': f'Appointment successfully booked for {patient["name"]} with {doctor_name} on {appointment_date.strftime("%B %d, %Y at %I:%M %p")}',
            'appointment': {
                'id': result.id,
                'patient_name': result.patient_name,
                'doctor_name': result.doctor_name,
                'date': result.appointment_date.isoformat(),
                'status': result.status,
                'reason': result.reason
            }
        }
        
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        return {
            'action': 'error',
            'message': 'Sorry, there was an error booking your appointment. Please try again.',
            'error': str(e)
        }

async def handle_cancellation_with_real_data(entities: dict) -> dict:
    """Handle appointment cancellation with real database lookup"""
    try:
        patient_name = entities.get('patient_name')
        patient_phone = entities.get('phone')
        
        if not patient_name and not patient_phone:
            return {
                'action': 'patient_info_needed',
                'message': 'Please provide your name or phone number to find your appointments.',
                'suggestions': {
                    'example': 'Say: "Cancel appointment for John Smith" or provide your phone number'
                }
            }
        
        # Find patient
        patient = None
        if patient_name:
            patient = await voice_service.find_patient_by_voice_info(patient_name)
        elif patient_phone:
            patient = await voice_service.find_patient_by_voice_info(patient_phone)
        
        if not patient:
            return {
                'action': 'patient_not_found',
                'message': 'We could not find any patient records with that information.',
                'suggestions': {
                    'message': 'Please check the spelling of your name or provide your phone number.'
                }
            }
        
        # Get patient's upcoming appointments
        appointments = await appointment_service.get_appointments_by_patient(patient['id'])
        upcoming_appointments = [
            apt for apt in appointments 
            if apt.appointment_date > datetime.now() and apt.status == 'scheduled'
        ]
        
        if not upcoming_appointments:
            return {
                'action': 'no_appointments_found',
                'message': f'No upcoming appointments found for {patient["name"]}.',
                'suggestions': {
                    'message': 'You may have already cancelled your appointments or they may have been completed.'
                }
            }
        
        if len(upcoming_appointments) == 1:
            # Cancel the single appointment
            appointment = upcoming_appointments[0]
            success = await appointment_service.cancel_appointment(appointment.id)
            
            if success:
                return {
                    'action': 'appointment_cancelled',
                    'message': f'Your appointment with {appointment.doctor_name} on {appointment.appointment_date.strftime("%B %d, %Y at %I:%M %p")} has been cancelled.',
                    'cancelled_appointment': {
                        'id': appointment.id,
                        'doctor_name': appointment.doctor_name,
                        'date': appointment.appointment_date.isoformat()
                    }
                }
            else:
                return {
                    'action': 'cancellation_failed',
                    'message': 'Sorry, we could not cancel your appointment. Please contact our office directly.'
                }
        else:
            # Multiple appointments - ask which one to cancel
            appointment_list = []
            for apt in upcoming_appointments:
                appointment_list.append({
                    'id': apt.id,
                    'doctor_name': apt.doctor_name,
                    'date': apt.appointment_date.strftime("%B %d, %Y at %I:%M %p"),
                    'reason': apt.reason or 'General consultation'
                })
            
            return {
                'action': 'multiple_appointments_found',
                'message': f'We found {len(upcoming_appointments)} upcoming appointments for {patient["name"]}. Which one would you like to cancel?',
                'appointments': appointment_list,
                'suggestions': {
                    'message': 'Please specify which appointment you want to cancel by mentioning the doctor name or date.'
                }
            }
        
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return {
            'action': 'error',
            'message': 'Sorry, there was an error processing your cancellation request.',
            'error': str(e)
        }

async def handle_reschedule_with_real_data(entities: dict) -> dict:
    """Handle appointment rescheduling with real database lookup"""
    try:
        patient_name = entities.get('patient_name')
        
        if not patient_name:
            return {
                'action': 'patient_info_needed',
                'message': 'Please provide your name to find your appointments for rescheduling.',
                'suggestions': {
                    'example': 'Say: "Reschedule appointment for John Smith"'
                }
            }
        
        # Find patient
        patient = await voice_service.find_patient_by_voice_info(patient_name)
        
        if not patient:
            return {
                'action': 'patient_not_found',
                'message': 'We could not find any patient records with that name.',
                'suggestions': {
                    'message': 'Please check the spelling of your name or provide your phone number.'
                }
            }
        
        # Get patient's appointments that can be rescheduled
        appointments = await appointment_service.get_appointments_by_patient(patient['id'])
        reschedulable_appointments = [
            apt for apt in appointments 
            if apt.appointment_date > datetime.now() and apt.status == 'scheduled'
        ]
        
        if not reschedulable_appointments:
            return {
                'action': 'no_appointments_found',
                'message': f'No upcoming appointments found for {patient["name"]} that can be rescheduled.'
            }
        
        # Check if new date/time provided
        new_date = entities.get('date')
        new_time = entities.get('time')
        
        if new_date and new_time:
            # Handle direct rescheduling
            try:
                if "tomorrow" in new_date.lower():
                    new_appointment_date = datetime.now() + timedelta(days=1)
                elif "today" in new_date.lower():
                    new_appointment_date = datetime.now()
                else:
                    new_appointment_date = datetime.strptime(new_date, "%Y-%m-%d")
                
                time_obj = datetime.strptime(new_time, "%H:%M").time()
                new_appointment_date = new_appointment_date.replace(
                    hour=time_obj.hour,
                    minute=time_obj.minute,
                    second=0,
                    microsecond=0
                )
                
                if len(reschedulable_appointments) == 1:
                    appointment = reschedulable_appointments[0]
                    
                    # Check availability for new slot
                    available_slots = await voice_service.get_available_slots_for_doctor(
                        appointment.doctor_name, 
                        new_appointment_date
                    )
                    
                    if new_time not in available_slots:
                        return {
                            'action': 'slot_unavailable',
                            'message': f'The requested time slot is not available for {appointment.doctor_name}.',
                            'suggestions': {
                                'available_slots': available_slots[:10],
                                'date': new_appointment_date.strftime("%Y-%m-%d"),
                                'doctor': appointment.doctor_name
                            }
                        }
                    
                    # Update appointment
                    from models.appointment import AppointmentUpdate
                    update_data = AppointmentUpdate(appointment_date=new_appointment_date)
                    updated_appointment = await appointment_service.update_appointment(appointment.id, update_data)
                    
                    if updated_appointment:
                        return {
                            'action': 'appointment_rescheduled',
                            'message': f'Your appointment with {appointment.doctor_name} has been rescheduled to {new_appointment_date.strftime("%B %d, %Y at %I:%M %p")}',
                            'appointment': {
                                'id': updated_appointment.id,
                                'doctor_name': updated_appointment.doctor_name,
                                'old_date': appointment.appointment_date.isoformat(),
                                'new_date': updated_appointment.appointment_date.isoformat()
                            }
                        }
                
            except ValueError as e:
                return {
                    'action': 'invalid_datetime',
                    'message': f'Invalid date or time format: {e}'
                }
        
        # Show available appointments to reschedule
        appointment_list = []
        for apt in reschedulable_appointments:
            appointment_list.append({
                'id': apt.id,
                'doctor_name': apt.doctor_name,
                'current_date': apt.appointment_date.strftime("%B %d, %Y at %I:%M %p"),
                'reason': apt.reason or 'General consultation'
            })
        
        return {
            'action': 'show_appointments_for_reschedule',
            'message': f'Here are your upcoming appointments that can be rescheduled:',
            'appointments': appointment_list,
            'suggestions': {
                'message': 'Please specify which appointment you want to reschedule and your preferred new date and time.',
                'example': 'Say: "Reschedule my appointment with Dr. Smith to tomorrow at 3 PM"'
            }
        }
        
    except Exception as e:
        logger.error(f"Error rescheduling appointment: {e}")
        return {
            'action': 'error',
            'message': 'Sorry, there was an error processing your reschedule request.',
            'error': str(e)
        }

@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    """Real-time voice processing WebSocket endpoint with enhanced database integration"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data.get("type") == "audio":
                # Decode base64 audio data
                audio_data = base64.b64decode(data["audio"])
                
                # Process through enhanced voice pipeline with real database data
                result = await voice_service.process_audio_stream(audio_data)
                
                # Handle appointment actions based on intent with real data
                if result.get("ai_response", {}).get("intent") in ["book_appointment", "cancel_appointment", "reschedule_appointment"]:
                    appointment_result = await handle_appointment_action_with_real_data({
                        'intent': result["ai_response"]["intent"],
                        'entities': result["ai_response"]["extracted_info"]
                    })
                    result["appointment_action"] = appointment_result
                
                # Send result back to client
                await websocket.send_text(json.dumps(result))
            
            elif data.get("type") == "reset":
                # Reset conversation context
                voice_service.reset_conversation()
                await websocket.send_text(json.dumps({"status": "conversation_reset"}))
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_text(json.dumps({"error": str(e)}))

@router.get("/conversation")
async def get_conversation_history():
    """Get current conversation history"""
    try:
        history = voice_service.get_conversation_history()
        return {"conversation": history}
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation history")

@router.post("/conversation/reset")
async def reset_conversation():
    """Reset conversation context"""
    try:
        voice_service.reset_conversation()
        return {"message": "Conversation reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset conversation")

@router.get("/health")
async def voice_health_check():
    """Check health of voice service and database connectivity"""
    try:
        health = voice_service.health_check()
        
        # Add real-time database stats
        try:
            doctors = await voice_service.get_real_doctors_data()
            recent_appointments = await voice_service.get_real_appointment_data()
            
            health["database_stats"] = {
                "available_doctors": len([d for d in doctors if d['is_available']]),
                "total_doctors": len(doctors),
                "recent_appointments": len(recent_appointments)
            }
        except Exception as e:
            health["database_stats"] = {"error": str(e)}
        
        return health
    except Exception as e:
        logger.error(f"Error in voice health check: {e}")
        raise HTTPException(status_code=500, detail="Failed to check voice service health")

@router.get("/doctors/available")
async def get_available_doctors_for_voice():
    """Get available doctors for voice interface"""
    try:
        doctors = await voice_service.get_real_doctors_data()
        available_doctors = [doc for doc in doctors if doc['is_available']]
        
        return {
            "available_doctors": available_doctors,
            "total_available": len(available_doctors),
            "specialties": list(set([doc['specialty'] for doc in available_doctors]))
        }
    except Exception as e:
        logger.error(f"Error getting available doctors: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available doctors")