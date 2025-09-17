// frontend/src/App.tsx
import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuth } from './stores/authStore';
import { UserRole } from './types/auth';

// Auth Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

// Protected Components
import ProtectedRoute, { DoctorRoute, PatientRoute, AdminRoute } from './components/ProtectedRoute';
import Layout from './components/Layout';

// Main Components
import Dashboard from './components/Dashboard';
import VoiceInterface from './components/VoiceInterface';
import PatientsList from './components/PatientsList';
import DoctorsList from './components/DoctorsList';
import AppointmentsList from './components/AppointmentsList';

// Forms
import AppointmentForm from './components/AppointmentForm';
import PatientForm from './components/PatientForm';
import DoctorForm from './components/DoctorForm';

// Profile and Settings
import ProfilePage from './pages/ProfilePage';
import SettingsPage from './pages/SettingsPage';

import './index.css';

// Type definitions for our entities
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

interface Patient {
  id?: string;
  patient_id?: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  medical_history?: string[];
  allergies?: string[];
  medications?: string[];
  insurance_provider?: string;
  insurance_id?: string;
  notes?: string;
  is_active: boolean;
}

interface Doctor {
  id?: string;
  doctor_id?: string;
  first_name: string;
  last_name: string;
  title: string;
  specialty: string;
  department?: string;
  email?: string;
  phone?: string;
  office_location?: string;
  education?: string[];
  certifications?: string[];
  years_experience?: number;
  languages?: string[];
  bio?: string;
  consultation_fee?: number;
  working_hours?: any[];
  is_available: boolean;
  is_active: boolean;
  rating?: number;
  total_reviews: number;
}

function App() {
  const { user, isAuthenticated, isLoading, checkAuth } = useAuth();
  
  // Form states
  const [showAppointmentForm, setShowAppointmentForm] = useState(false);
  const [showPatientForm, setShowPatientForm] = useState(false);
  const [showDoctorForm, setShowDoctorForm] = useState(false);
  
  // Edit states
  const [editingAppointment, setEditingAppointment] = useState<Appointment | null>(null);
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null);

  // Refresh keys to trigger re-fetch of data
  const [refreshKeys, setRefreshKeys] = useState({
    appointments: 0,
    patients: 0,
    doctors: 0,
    dashboard: 0
  });

  useEffect(() => {
    // Check authentication on app load
    checkAuth();
  }, [checkAuth]);

  // Form handlers
  const handleCreateNewAppointment = () => {
    setEditingAppointment(null);
    setShowAppointmentForm(true);
  };

  const handleEditAppointment = (appointment: any) => {
    setEditingAppointment(appointment);
    setShowAppointmentForm(true);
  };

  const handleSaveAppointment = (appointment: Appointment) => {
    setRefreshKeys(prev => ({ ...prev, appointments: prev.appointments + 1, dashboard: prev.dashboard + 1 }));
    setShowAppointmentForm(false);
    setEditingAppointment(null);
  };

  const handleCreateNewPatient = () => {
    setEditingPatient(null);
    setShowPatientForm(true);
  };

  const handleEditPatient = (patient: any) => {
    setEditingPatient(patient);
    setShowPatientForm(true);
  };

  const handleSavePatient = (patient: Patient) => {
    setRefreshKeys(prev => ({ ...prev, patients: prev.patients + 1, dashboard: prev.dashboard + 1 }));
    setShowPatientForm(false);
    setEditingPatient(null);
  };

  const handleCreateNewDoctor = () => {
    setEditingDoctor(null);
    setShowDoctorForm(true);
  };

  const handleEditDoctor = (doctor: any) => {
    setEditingDoctor(doctor);
    setShowDoctorForm(true);
  };

  const handleSaveDoctor = (doctor: Doctor) => {
    setRefreshKeys(prev => ({ ...prev, doctors: prev.doctors + 1, dashboard: prev.dashboard + 1 }));
    setShowDoctorForm(false);
    setEditingDoctor(null);
  };

  const handleCancelAppointment = async (appointment: any) => {
    try {
      const response = await fetch(`/api/appointments/${appointment.id}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setRefreshKeys(prev => ({ ...prev, appointments: prev.appointments + 1, dashboard: prev.dashboard + 1 }));
      }
    } catch (error) {
      console.error('Error cancelling appointment:', error);
    }
  };

  const handleNavigate = (section: string) => {
    // This function can be used to programmatically navigate
    console.log('Navigate to:', section);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-cyan-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading DocTalk AI...</p>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Public Routes */}
          <Route 
            path="/login" 
            element={
              isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />
            } 
          />
          <Route 
            path="/register" 
            element={
              isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />
            } 
          />

          {/* Protected Routes */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    {/* Dashboard - Available to all authenticated users */}
                    <Route 
                      path="/dashboard" 
                      element={
                        <Dashboard 
                          key={refreshKeys.dashboard} 
                          onNavigate={handleNavigate} 
                        />
                      } 
                    />
                    
                    {/* Voice Interface - Available to all authenticated users */}
                    <Route path="/voice" element={<VoiceInterface />} />
                    
                    {/* Profile and Settings - Available to all authenticated users */}
                    <Route path="/profile" element={<ProfilePage />} />
                    <Route path="/settings" element={<SettingsPage />} />

                    {/* Patient Management - Admins and Doctors can manage, Patients can view their own */}
                    <Route 
                      path="/patients" 
                      element={
                        <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.DOCTOR, UserRole.PATIENT]}>
                          <PatientsList 
                            key={refreshKeys.patients}
                            onCreateNew={handleCreateNewPatient}
                            onEdit={handleEditPatient}
                            onPatientSelect={(patient) => console.log('Select patient:', patient)}
                          />
                        </ProtectedRoute>
                      } 
                    />

                    {/* Doctor Management - Admins can manage, others can view */}
                    <Route 
                      path="/doctors" 
                      element={
                        <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.DOCTOR, UserRole.PATIENT]}>
                          <DoctorsList 
                            key={refreshKeys.doctors}
                            onCreateNew={handleCreateNewDoctor}
                            onEdit={handleEditDoctor}
                            onDoctorSelect={(doctor) => console.log('Select doctor:', doctor)}
                          />
                        </ProtectedRoute>
                      } 
                    />

                    {/* Appointments - Role-based access */}
                    <Route 
                      path="/appointments" 
                      element={
                        <ProtectedRoute allowedRoles={[UserRole.ADMIN, UserRole.DOCTOR, UserRole.PATIENT]}>
                          <AppointmentsList 
                            key={refreshKeys.appointments}
                            onCreateNew={handleCreateNewAppointment}
                            onEdit={handleEditAppointment}
                            onCancel={handleCancelAppointment}
                            onAppointmentSelect={(appointment) => console.log('Select appointment:', appointment)}
                          />
                        </ProtectedRoute>
                      } 
                    />

                    {/* Doctor-only Routes */}
                    <Route 
                      path="/doctor/appointments" 
                      element={
                        <DoctorRoute>
                          <AppointmentsList 
                            key={refreshKeys.appointments}
                            onCreateNew={handleCreateNewAppointment}
                            onEdit={handleEditAppointment}
                            onCancel={handleCancelAppointment}
                            onAppointmentSelect={(appointment) => console.log('Select appointment:', appointment)}
                          />
                        </DoctorRoute>
                      } 
                    />
                    <Route 
                      path="/doctor/patients" 
                      element={
                        <DoctorRoute>
                          <PatientsList 
                            key={refreshKeys.patients}
                            onCreateNew={handleCreateNewPatient}
                            onEdit={handleEditPatient}
                            onPatientSelect={(patient) => console.log('Select patient:', patient)}
                          />
                        </DoctorRoute>
                      } 
                    />

                    {/* Patient-only Routes */}
                    <Route 
                      path="/patient/appointments" 
                      element={
                        <PatientRoute>
                          <AppointmentsList 
                            key={refreshKeys.appointments}
                            onCreateNew={handleCreateNewAppointment}
                            onEdit={handleEditAppointment}
                            onCancel={handleCancelAppointment}
                            onAppointmentSelect={(appointment) => console.log('Select appointment:', appointment)}
                          />
                        </PatientRoute>
                      } 
                    />
                    <Route 
                      path="/patient/book-appointment" 
                      element={
                        <PatientRoute>
                          <div>Patient Appointment Booking (Using Modal)</div>
                        </PatientRoute>
                      } 
                    />

                    {/* Admin-only Routes */}
                    <Route 
                      path="/admin/users" 
                      element={
                        <AdminRoute>
                          <div>User Management (Coming Soon)</div>
                        </AdminRoute>
                      } 
                    />
                    <Route 
                      path="/admin/analytics" 
                      element={
                        <AdminRoute>
                          <div>Analytics Dashboard (Coming Soon)</div>
                        </AdminRoute>
                      } 
                    />

                    {/* Default redirect */}
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    
                    {/* 404 Page */}
                    <Route 
                      path="*" 
                      element={
                        <div className="min-h-screen flex items-center justify-center bg-gray-50">
                          <div className="text-center">
                            <h1 className="text-4xl font-bold text-gray-900 mb-4">404</h1>
                            <p className="text-gray-600 mb-4">Page not found</p>
                            <button
                              onClick={() => window.history.back()}
                              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                            >
                              Go Back
                            </button>
                          </div>
                        </div>
                      } 
                    />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>

        {/* Forms/Modals */}
        <AppointmentForm
          isOpen={showAppointmentForm}
          onClose={() => {
            setShowAppointmentForm(false);
            setEditingAppointment(null);
          }}
          appointment={editingAppointment}
          onSave={handleSaveAppointment}
        />

        <PatientForm
          isOpen={showPatientForm}
          onClose={() => {
            setShowPatientForm(false);
            setEditingPatient(null);
          }}
          patient={editingPatient}
          onSave={handleSavePatient}
        />

        <DoctorForm
          isOpen={showDoctorForm}
          onClose={() => {
            setShowDoctorForm(false);
            setEditingDoctor(null);
          }}
          doctor={editingDoctor}
          onSave={handleSaveDoctor}
        />

        {/* Global Toast Notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#fff',
              color: '#374151',
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
              border: '1px solid #e5e7eb',
              borderRadius: '12px',
            },
            success: {
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </div>
    </Router>
  );
}

export default App;