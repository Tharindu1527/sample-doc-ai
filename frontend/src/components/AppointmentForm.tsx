import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Calendar, Clock, User, Phone, Save, AlertCircle } from 'lucide-react';
import { makeAuthenticatedRequest, useAuth } from '../stores/authStore';
import { UserRole } from '../types/auth';
import toast from 'react-hot-toast';

interface Doctor {
  id: string;
  doctor_id: string;
  first_name: string;
  last_name: string;
  specialty: string;
  is_available: boolean;
}

interface Patient {
  id: string;
  patient_id: string;
  first_name: string;
  last_name: string;
  phone?: string;
  email?: string;
}

interface Appointment {
  id?: string;
  patient_id: string;
  patient_name: string;
  patient_phone?: string;
  patient_email?: string;
  doctor_name: string;
  appointment_date: string;
  duration_minutes: number;
  status: string;
  reason?: string;
  notes?: string;
}

interface AppointmentFormProps {
  isOpen: boolean;
  onClose: () => void;
  appointment?: Appointment | null;
  onSave: (appointment: Appointment) => void;
}

const AppointmentForm: React.FC<AppointmentFormProps> = ({
  isOpen,
  onClose,
  appointment,
  onSave
}) => {
  const { user, isAuthenticated } = useAuth();
  const [formData, setFormData] = useState<Appointment>({
    patient_id: '',
    patient_name: '',
    patient_phone: '',
    patient_email: '',
    doctor_name: '',
    appointment_date: '',
    duration_minutes: 30,
    status: 'scheduled',
    reason: '',
    notes: ''
  });

  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchPatient, setSearchPatient] = useState('');
  const [showPatientDropdown, setShowPatientDropdown] = useState(false);

  useEffect(() => {
    if (isOpen && isAuthenticated) {
      fetchDoctors();
      if (user?.role !== UserRole.PATIENT) {
        fetchPatients();
      }
      
      if (appointment) {
        setFormData(appointment);
      } else {
        // Reset form for new appointment
        const initialData: Appointment = {
          patient_id: '',
          patient_name: '',
          patient_phone: '',
          patient_email: '',
          doctor_name: '',
          appointment_date: '',
          duration_minutes: 30,
          status: 'scheduled',
          reason: '',
          notes: ''
        };

        // If user is a patient, pre-fill their information
        if (user?.role === UserRole.PATIENT) {
          initialData.patient_id = user.patient_id || '';
          initialData.patient_name = `${user.first_name} ${user.last_name}`;
          initialData.patient_email = user.email;
          initialData.patient_phone = user.phone || '';
        }

        setFormData(initialData);
      }
    }
  }, [isOpen, appointment, isAuthenticated, user]);

  const fetchDoctors = async () => {
    try {
      console.log('Fetching doctors...');
      const data = await makeAuthenticatedRequest('/api/doctors/available');
      console.log('Doctors fetched:', data.length);
      setDoctors(data);
    } catch (error) {
      console.error('Error fetching doctors:', error);
      toast.error('Failed to load doctors');
    }
  };

  const fetchPatients = async () => {
    try {
      console.log('Fetching patients...');
      const data = await makeAuthenticatedRequest('/api/patients/');
      console.log('Patients fetched:', data.length);
      setPatients(data);
    } catch (error) {
      console.error('Error fetching patients:', error);
      toast.error('Failed to load patients');
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.patient_name.trim()) {
      newErrors.patient_name = 'Patient name is required';
    }

    if (!formData.doctor_name) {
      newErrors.doctor_name = 'Doctor selection is required';
    }

    if (!formData.appointment_date) {
      newErrors.appointment_date = 'Appointment date is required';
    } else {
      const appointmentDate = new Date(formData.appointment_date);
      const now = new Date();
      if (appointmentDate < now) {
        newErrors.appointment_date = 'Appointment date cannot be in the past';
      }
    }

    if (formData.patient_phone && !/^\+?[\d\s\-\(\)]+$/.test(formData.patient_phone)) {
      newErrors.patient_phone = 'Please enter a valid phone number';
    }

    if (formData.patient_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.patient_email)) {
      newErrors.patient_email = 'Please enter a valid email address';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    if (!isAuthenticated) {
      toast.error('Please log in to create appointments');
      return;
    }

    setLoading(true);
    
    try {
      const method = appointment?.id ? 'PUT' : 'POST';
      const url = appointment?.id 
        ? `/api/appointments/${appointment.id}`
        : '/api/appointments/';

      console.log('Submitting appointment:', formData);
      console.log('Request method:', method, 'URL:', url);

      const savedAppointment = await makeAuthenticatedRequest(url, {
        method,
        body: JSON.stringify(formData),
      });

      console.log('Appointment saved:', savedAppointment);
      onSave(savedAppointment);
      toast.success(appointment?.id ? 'Appointment updated successfully!' : 'Appointment created successfully!');
      onClose();
    } catch (error) {
      console.error('Error saving appointment:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to save appointment';
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handlePatientSelect = (patient: Patient) => {
    setFormData({
      ...formData,
      patient_id: patient.patient_id,
      patient_name: `${patient.first_name} ${patient.last_name}`,
      patient_phone: patient.phone || '',
      patient_email: patient.email || ''
    });
    setSearchPatient(`${patient.first_name} ${patient.last_name}`);
    setShowPatientDropdown(false);
  };

  const filteredPatients = patients.filter(patient =>
    `${patient.first_name} ${patient.last_name}`.toLowerCase().includes(searchPatient.toLowerCase())
  );

  if (!isOpen) return null;

  // Show authentication error
  if (!isAuthenticated) {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-center">
              <AlertCircle className="w-16 h-16 text-red-300 mx-auto mb-4" />
              <h2 className="text-xl font-bold text-red-900 mb-2">Authentication Required</h2>
              <p className="text-red-600 mb-4">Please log in to create appointments</p>
              <button
                onClick={() => window.location.href = '/login'}
                className="btn-primary w-full"
              >
                Go to Login
              </button>
            </div>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-100 p-2 rounded-lg">
                <Calendar className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {appointment?.id ? 'Edit Appointment' : 'New Appointment'}
                </h2>
                <p className="text-sm text-gray-600">
                  {appointment?.id ? 'Update appointment details' : 'Schedule a new appointment'}
                </p>
                {user && (
                  <p className="text-xs text-gray-500">
                    Creating as: {user.first_name} {user.last_name} ({user.role})
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Patient Selection - Only show for doctors and admins */}
            {user?.role !== UserRole.PATIENT && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <User className="w-5 h-5 mr-2" />
                  Patient Information
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="relative">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Patient Name *
                    </label>
                    <input
                      type="text"
                      value={searchPatient || formData.patient_name}
                      onChange={(e) => {
                        setSearchPatient(e.target.value);
                        setFormData({ ...formData, patient_name: e.target.value });
                        setShowPatientDropdown(true);
                      }}
                      onFocus={() => setShowPatientDropdown(true)}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                        errors.patient_name ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="Search or enter patient name"
                    />
                    
                    {/* Patient Dropdown */}
                    {showPatientDropdown && filteredPatients.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                        {filteredPatients.slice(0, 5).map((patient) => (
                          <button
                            key={patient.id}
                            type="button"
                            onClick={() => handlePatientSelect(patient)}
                            className="w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-100 last:border-b-0"
                          >
                            <div className="font-medium">{patient.first_name} {patient.last_name}</div>
                            <div className="text-sm text-gray-500">ID: {patient.patient_id}</div>
                          </button>
                        ))}
                      </div>
                    )}
                    
                    {errors.patient_name && (
                      <p className="text-red-500 text-sm mt-1">{errors.patient_name}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Patient Phone
                    </label>
                    <input
                      type="tel"
                      value={formData.patient_phone}
                      onChange={(e) => setFormData({ ...formData, patient_phone: e.target.value })}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                        errors.patient_phone ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="+1 (555) 123-4567"
                    />
                    {errors.patient_phone && (
                      <p className="text-red-500 text-sm mt-1">{errors.patient_phone}</p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Patient Email
                  </label>
                  <input
                    type="email"
                    value={formData.patient_email}
                    onChange={(e) => setFormData({ ...formData, patient_email: e.target.value })}
                    className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.patient_email ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="patient@example.com"
                  />
                  {errors.patient_email && (
                    <p className="text-red-500 text-sm mt-1">{errors.patient_email}</p>
                  )}
                </div>
              </div>
            )}

            {/* Patient info display for patients */}
            {user?.role === UserRole.PATIENT && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <User className="w-5 h-5 mr-2" />
                  Patient Information
                </h3>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-blue-800">
                    <strong>Patient:</strong> {formData.patient_name}
                  </p>
                  <p className="text-sm text-blue-800">
                    <strong>Email:</strong> {formData.patient_email}
                  </p>
                  {formData.patient_phone && (
                    <p className="text-sm text-blue-800">
                      <strong>Phone:</strong> {formData.patient_phone}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Appointment Details */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <Calendar className="w-5 h-5 mr-2" />
                Appointment Details
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Doctor *
                  </label>
                  <select
                    value={formData.doctor_name}
                    onChange={(e) => setFormData({ ...formData, doctor_name: e.target.value })}
                    className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.doctor_name ? 'border-red-500' : 'border-gray-300'
                    }`}
                  >
                    <option value="">Select a doctor</option>
                    {doctors.map((doctor) => (
                      <option key={doctor.id} value={`Dr. ${doctor.first_name} ${doctor.last_name}`}>
                        Dr. {doctor.first_name} {doctor.last_name} - {doctor.specialty}
                      </option>
                    ))}
                  </select>
                  {errors.doctor_name && (
                    <p className="text-red-500 text-sm mt-1">{errors.doctor_name}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Duration (minutes)
                  </label>
                  <select
                    value={formData.duration_minutes}
                    onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value={15}>15 minutes</option>
                    <option value={30}>30 minutes</option>
                    <option value={45}>45 minutes</option>
                    <option value={60}>60 minutes</option>
                    <option value={90}>90 minutes</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Date & Time *
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.appointment_date}
                    onChange={(e) => setFormData({ ...formData, appointment_date: e.target.value })}
                    className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.appointment_date ? 'border-red-500' : 'border-gray-300'
                    }`}
                    min={new Date().toISOString().slice(0, 16)}
                  />
                  {errors.appointment_date && (
                    <p className="text-red-500 text-sm mt-1">{errors.appointment_date}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Status
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={user?.role === UserRole.PATIENT}
                  >
                    <option value="scheduled">Scheduled</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                    <option value="rescheduled">Rescheduled</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason for Visit
                </label>
                <input
                  type="text"
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., Regular checkup, Follow-up visit"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={3}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Additional notes about the appointment"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end space-x-3 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={onClose}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>{loading ? 'Saving...' : 'Save Appointment'}</span>
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default AppointmentForm;