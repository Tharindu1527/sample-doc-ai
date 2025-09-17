import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, UserCheck, Mail, Phone, MapPin, Save, Award, Clock } from 'lucide-react';
import toast from 'react-hot-toast';

interface WorkingHours {
  day: string;
  start_time: string;
  end_time: string;
  is_available: boolean;
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
  working_hours?: WorkingHours[];
  is_available: boolean;
  is_active: boolean;
  rating?: number;
  total_reviews: number;
}

interface DoctorFormProps {
  isOpen: boolean;
  onClose: () => void;
  doctor?: Doctor | null;
  onSave: (doctor: Doctor) => void;
}

const DoctorForm: React.FC<DoctorFormProps> = ({
  isOpen,
  onClose,
  doctor,
  onSave
}) => {
  const [formData, setFormData] = useState<Doctor>({
    first_name: '',
    last_name: '',
    title: 'Dr.',
    specialty: '',
    department: '',
    email: '',
    phone: '',
    office_location: '',
    education: [],
    certifications: [],
    years_experience: 0,
    languages: [],
    bio: '',
    consultation_fee: 0,
    working_hours: [
      { day: 'Monday', start_time: '09:00', end_time: '17:00', is_available: true },
      { day: 'Tuesday', start_time: '09:00', end_time: '17:00', is_available: true },
      { day: 'Wednesday', start_time: '09:00', end_time: '17:00', is_available: true },
      { day: 'Thursday', start_time: '09:00', end_time: '17:00', is_available: true },
      { day: 'Friday', start_time: '09:00', end_time: '17:00', is_available: true },
      { day: 'Saturday', start_time: '09:00', end_time: '13:00', is_available: false },
      { day: 'Sunday', start_time: '09:00', end_time: '13:00', is_available: false }
    ],
    is_available: true,
    is_active: true,
    total_reviews: 0
  });

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [currentTab, setCurrentTab] = useState<'basic' | 'contact' | 'professional' | 'schedule'>('basic');

  // Form fields for arrays
  const [newEducation, setNewEducation] = useState('');
  const [newCertification, setNewCertification] = useState('');
  const [newLanguage, setNewLanguage] = useState('');

  const specialties = [
    'General Practice',
    'Cardiology',
    'Dermatology',
    'Emergency Medicine',
    'Family Medicine',
    'Internal Medicine',
    'Neurology',
    'Obstetrics & Gynecology',
    'Oncology',
    'Ophthalmology',
    'Orthopedics',
    'Pediatrics',
    'Psychiatry',
    'Radiology',
    'Surgery',
    'Urology'
  ];

  const departments = [
    'Emergency Department',
    'Internal Medicine',
    'Surgery',
    'Pediatrics',
    'Obstetrics & Gynecology',
    'Cardiology',
    'Neurology',
    'Oncology',
    'Radiology',
    'Psychiatry',
    'Orthopedics',
    'Dermatology',
    'Ophthalmology',
    'Urology'
  ];

  useEffect(() => {
    if (isOpen) {
      if (doctor) {
        setFormData({
          ...doctor,
          education: doctor.education || [],
          certifications: doctor.certifications || [],
          languages: doctor.languages || [],
          working_hours: doctor.working_hours || [
            { day: 'Monday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Tuesday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Wednesday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Thursday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Friday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Saturday', start_time: '09:00', end_time: '13:00', is_available: false },
            { day: 'Sunday', start_time: '09:00', end_time: '13:00', is_available: false }
          ]
        });
      } else {
        // Reset form for new doctor
        setFormData({
          first_name: '',
          last_name: '',
          title: 'Dr.',
          specialty: '',
          department: '',
          email: '',
          phone: '',
          office_location: '',
          education: [],
          certifications: [],
          years_experience: 0,
          languages: [],
          bio: '',
          consultation_fee: 0,
          working_hours: [
            { day: 'Monday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Tuesday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Wednesday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Thursday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Friday', start_time: '09:00', end_time: '17:00', is_available: true },
            { day: 'Saturday', start_time: '09:00', end_time: '13:00', is_available: false },
            { day: 'Sunday', start_time: '09:00', end_time: '13:00', is_available: false }
          ],
          is_available: true,
          is_active: true,
          total_reviews: 0
        });
      }
      setCurrentTab('basic');
      setErrors({});
    }
  }, [isOpen, doctor]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.first_name.trim()) {
      newErrors.first_name = 'First name is required';
    }

    if (!formData.last_name.trim()) {
      newErrors.last_name = 'Last name is required';
    }

    if (!formData.specialty) {
      newErrors.specialty = 'Specialty is required';
    }

    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (formData.phone && !/^\+?[\d\s\-\(\)]+$/.test(formData.phone)) {
      newErrors.phone = 'Please enter a valid phone number';
    }

    if (formData.years_experience && formData.years_experience < 0) {
      newErrors.years_experience = 'Years of experience cannot be negative';
    }

    if (formData.consultation_fee && formData.consultation_fee < 0) {
      newErrors.consultation_fee = 'Consultation fee cannot be negative';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    
    try {
      const method = doctor?.id ? 'PUT' : 'POST';
      const url = doctor?.id 
        ? `/api/doctors/${doctor.id}`
        : '/api/doctors/';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        const savedDoctor = await response.json();
        onSave(savedDoctor);
        toast.success(doctor?.id ? 'Doctor updated successfully!' : 'Doctor created successfully!');
        onClose();
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || 'Failed to save doctor');
      }
    } catch (error) {
      console.error('Error saving doctor:', error);
      toast.error('Failed to save doctor');
    } finally {
      setLoading(false);
    }
  };

  const addToArray = (field: 'education' | 'certifications' | 'languages', value: string) => {
    if (value.trim()) {
      setFormData({
        ...formData,
        [field]: [...(formData[field] || []), value.trim()]
      });
      
      // Clear the input
      if (field === 'education') setNewEducation('');
      if (field === 'certifications') setNewCertification('');
      if (field === 'languages') setNewLanguage('');
    }
  };

  const removeFromArray = (field: 'education' | 'certifications' | 'languages', index: number) => {
    const newArray = [...(formData[field] || [])];
    newArray.splice(index, 1);
    setFormData({
      ...formData,
      [field]: newArray
    });
  };

  const updateWorkingHours = (index: number, updates: Partial<WorkingHours>) => {
    const newWorkingHours = [...formData.working_hours!];
    newWorkingHours[index] = { ...newWorkingHours[index], ...updates };
    setFormData({
      ...formData,
      working_hours: newWorkingHours
    });
  };

  const tabs = [
    { id: 'basic', label: 'Basic Info', icon: UserCheck },
    { id: 'contact', label: 'Contact', icon: Phone },
    { id: 'professional', label: 'Professional', icon: Award },
    { id: 'schedule', label: 'Schedule', icon: Clock }
  ];

  if (!isOpen) return null;

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
          className="bg-white rounded-2xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="bg-green-100 p-2 rounded-lg">
                <UserCheck className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {doctor?.id ? 'Edit Doctor' : 'New Doctor'}
                </h2>
                <p className="text-sm text-gray-600">
                  {doctor?.id ? 'Update doctor information' : 'Add a new doctor to the system'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setCurrentTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                    currentTab === tab.id
                      ? 'border-green-500 text-green-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6">
            {/* Basic Information Tab */}
            {currentTab === 'basic' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Title
                    </label>
                    <select
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    >
                      <option value="Dr.">Dr.</option>
                      <option value="Prof.">Prof.</option>
                      <option value="Prof. Dr.">Prof. Dr.</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      First Name *
                    </label>
                    <input
                      type="text"
                      value={formData.first_name}
                      onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
                        errors.first_name ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="Enter first name"
                    />
                    {errors.first_name && (
                      <p className="text-red-500 text-sm mt-1">{errors.first_name}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Last Name *
                    </label>
                    <input
                      type="text"
                      value={formData.last_name}
                      onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
                        errors.last_name ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="Enter last name"
                    />
                    {errors.last_name && (
                      <p className="text-red-500 text-sm mt-1">{errors.last_name}</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Specialty *
                    </label>
                    <select
                      value={formData.specialty}
                      onChange={(e) => setFormData({ ...formData, specialty: e.target.value })}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
                        errors.specialty ? 'border-red-500' : 'border-gray-300'
                      }`}
                    >
                      <option value="">Select specialty</option>
                      {specialties.map((specialty) => (
                        <option key={specialty} value={specialty}>
                          {specialty}
                        </option>
                      ))}
                    </select>
                    {errors.specialty && (
                      <p className="text-red-500 text-sm mt-1">{errors.specialty}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Department
                    </label>
                    <select
                      value={formData.department}
                      onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    >
                      <option value="">Select department</option>
                      {departments.map((department) => (
                        <option key={department} value={department}>
                          {department}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Years of Experience
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={formData.years_experience || ''}
                      onChange={(e) => setFormData({ ...formData, years_experience: parseInt(e.target.value) || 0 })}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
                        errors.years_experience ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="0"
                    />
                    {errors.years_experience && (
                      <p className="text-red-500 text-sm mt-1">{errors.years_experience}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Consultation Fee ($)
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.consultation_fee || ''}
                      onChange={(e) => setFormData({ ...formData, consultation_fee: parseFloat(e.target.value) || 0 })}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
                        errors.consultation_fee ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="0.00"
                    />
                    {errors.consultation_fee && (
                      <p className="text-red-500 text-sm mt-1">{errors.consultation_fee}</p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Bio
                  </label>
                  <textarea
                    value={formData.bio}
                    onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                    rows={4}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="Brief professional biography"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="is_available"
                      checked={formData.is_available}
                      onChange={(e) => setFormData({ ...formData, is_available: e.target.checked })}
                      className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                    />
                    <label htmlFor="is_available" className="ml-2 block text-sm text-gray-900">
                      Available for appointments
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="is_active"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                    />
                    <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900">
                      Active doctor
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* Contact Information Tab */}
            {currentTab === 'contact' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
                        errors.email ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="doctor@hospital.com"
                    />
                    {errors.email && (
                      <p className="text-red-500 text-sm mt-1">{errors.email}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Phone
                    </label>
                    <input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
                        errors.phone ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="+1 (555) 123-4567"
                    />
                    {errors.phone && (
                      <p className="text-red-500 text-sm mt-1">{errors.phone}</p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Office Location
                  </label>
                  <input
                    type="text"
                    value={formData.office_location}
                    onChange={(e) => setFormData({ ...formData, office_location: e.target.value })}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="Building, Floor, Room number"
                  />
                </div>

                {/* Languages */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Languages Spoken
                  </label>
                  <div className="flex space-x-2 mb-2">
                    <input
                      type="text"
                      value={newLanguage}
                      onChange={(e) => setNewLanguage(e.target.value)}
                      className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="Add language"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addToArray('languages', newLanguage);
                        }
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => addToArray('languages', newLanguage)}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {formData.languages?.map((language, index) => (
                      <span
                        key={index}
                        className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center"
                      >
                        {language}
                        <button
                          type="button"
                          onClick={() => removeFromArray('languages', index)}
                          className="ml-2 text-blue-600 hover:text-blue-800"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Professional Information Tab */}
            {currentTab === 'professional' && (
              <div className="space-y-6">
                {/* Education */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Education
                  </label>
                  <div className="flex space-x-2 mb-2">
                    <input
                      type="text"
                      value={newEducation}
                      onChange={(e) => setNewEducation(e.target.value)}
                      className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="Add education (e.g., MD from Harvard Medical School)"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addToArray('education', newEducation);
                        }
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => addToArray('education', newEducation)}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Add
                    </button>
                  </div>
                  <div className="space-y-2">
                    {formData.education?.map((edu, index) => (
                      <div
                        key={index}
                        className="bg-gray-100 p-3 rounded-lg flex items-center justify-between"
                      >
                        <span className="text-sm">{edu}</span>
                        <button
                          type="button"
                          onClick={() => removeFromArray('education', index)}
                          className="text-red-600 hover:text-red-800"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Certifications */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Certifications
                  </label>
                  <div className="flex space-x-2 mb-2">
                    <input
                      type="text"
                      value={newCertification}
                      onChange={(e) => setNewCertification(e.target.value)}
                      className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="Add certification"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addToArray('certifications', newCertification);
                        }
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => addToArray('certifications', newCertification)}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Add
                    </button>
                  </div>
                  <div className="space-y-2">
                    {formData.certifications?.map((cert, index) => (
                      <div
                        key={index}
                        className="bg-green-100 p-3 rounded-lg flex items-center justify-between"
                      >
                        <span className="text-sm">{cert}</span>
                        <button
                          type="button"
                          onClick={() => removeFromArray('certifications', index)}
                          className="text-red-600 hover:text-red-800"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Schedule Tab */}
            {currentTab === 'schedule' && (
              <div className="space-y-6">
                <h3 className="text-lg font-medium text-gray-900">Working Hours</h3>
                <div className="space-y-4">
                  {formData.working_hours?.map((schedule, index) => (
                    <div key={schedule.day} className="grid grid-cols-4 gap-4 items-center p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          checked={schedule.is_available}
                          onChange={(e) => updateWorkingHours(index, { is_available: e.target.checked })}
                          className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                        />
                        <span className="font-medium text-gray-900">{schedule.day}</span>
                      </div>
                      
                      <input
                        type="time"
                        value={schedule.start_time}
                        onChange={(e) => updateWorkingHours(index, { start_time: e.target.value })}
                        disabled={!schedule.is_available}
                        className="p-2 border border-gray-300 rounded focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:bg-gray-100"
                      />
                      
                      <input
                        type="time"
                        value={schedule.end_time}
                        onChange={(e) => updateWorkingHours(index, { end_time: e.target.value })}
                        disabled={!schedule.is_available}
                        className="p-2 border border-gray-300 rounded focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:bg-gray-100"
                      />
                      
                      <span className="text-sm text-gray-500">
                        {schedule.is_available ? 'Available' : 'Not available'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200">
              <div className="flex space-x-2">
                {tabs.map((tab, index) => (
                  <div
                    key={tab.id}
                    className={`w-2 h-2 rounded-full ${
                      currentTab === tab.id ? 'bg-green-600' : 'bg-gray-300'
                    }`}
                  />
                ))}
              </div>
              
              <div className="flex items-center space-x-3">
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
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  <span>{loading ? 'Saving...' : 'Save Doctor'}</span>
                </button>
              </div>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default DoctorForm;