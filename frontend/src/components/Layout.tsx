// frontend/src/components/Layout.tsx
import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Home, 
  Mic, 
  Users, 
  UserCheck, 
  Calendar,
  Menu,
  X,
  LogOut,
  Settings,
  User,
  Shield,
  Stethoscope,
  Heart,
  BarChart3
} from 'lucide-react';
import { useAuth, hasRole } from '../stores/authStore';
import { UserRole } from '../types/auth';
import toast from 'react-hot-toast';

interface LayoutProps {
  children: React.ReactNode;
}

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ComponentType<any>;
  path: string;
  roles: UserRole[];
  badge?: string;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const navigationItems: NavigationItem[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: Home,
      path: '/dashboard',
      roles: [UserRole.ADMIN, UserRole.DOCTOR, UserRole.PATIENT, UserRole.STAFF]
    },
    {
      id: 'voice',
      label: 'Voice Assistant',
      icon: Mic,
      path: '/voice',
      roles: [UserRole.ADMIN, UserRole.DOCTOR, UserRole.PATIENT, UserRole.STAFF]
    },
    {
      id: 'appointments',
      label: 'Appointments',
      icon: Calendar,
      path: user?.role === UserRole.DOCTOR ? '/doctor/appointments' : 
            user?.role === UserRole.PATIENT ? '/patient/appointments' : '/appointments',
      roles: [UserRole.ADMIN, UserRole.DOCTOR, UserRole.PATIENT, UserRole.STAFF]
    },
    {
      id: 'patients',
      label: 'Patients',
      icon: Users,
      path: user?.role === UserRole.DOCTOR ? '/doctor/patients' : '/patients',
      roles: [UserRole.ADMIN, UserRole.DOCTOR, UserRole.STAFF],
    },
    {
      id: 'doctors',
      label: 'Doctors',
      icon: UserCheck,
      path: '/doctors',
      roles: [UserRole.ADMIN, UserRole.PATIENT, UserRole.STAFF]
    },
    // Admin specific routes
    {
      id: 'admin-users',
      label: 'User Management',
      icon: Shield,
      path: '/admin/users',
      roles: [UserRole.ADMIN]
    },
    {
      id: 'admin-analytics',
      label: 'Analytics',
      icon: BarChart3,
      path: '/admin/analytics',
      roles: [UserRole.ADMIN]
    }
  ];

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully');
    navigate('/login');
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    setIsSidebarOpen(false);
  };

  const getUserIcon = () => {
    switch (user?.role) {
      case UserRole.DOCTOR:
        return <Stethoscope className="w-5 h-5" />;
      case UserRole.PATIENT:
        return <Heart className="w-5 h-5" />;
      case UserRole.ADMIN:
        return <Shield className="w-5 h-5" />;
      default:
        return <User className="w-5 h-5" />;
    }
  };

  const getRoleColor = () => {
    switch (user?.role) {
      case UserRole.DOCTOR:
        return 'text-green-600 bg-green-100';
      case UserRole.PATIENT:
        return 'text-blue-600 bg-blue-100';
      case UserRole.ADMIN:
        return 'text-purple-600 bg-purple-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getFilteredNavigationItems = () => {
    return navigationItems.filter(item => 
      user && hasRole(user, item.roles)
    );
  };

  const isActiveRoute = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <AnimatePresence>
        {(isSidebarOpen || window.innerWidth >= 1024) && (
          <motion.div
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed lg:static inset-y-0 left-0 z-50 w-72 bg-white shadow-xl lg:shadow-none flex flex-col"
          >
            {/* Sidebar Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h1 className="text-xl font-bold text-gray-900">DocTalk AI</h1>
                <p className="text-sm text-gray-600">Medical Practice Management</p>
              </div>
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="lg:hidden p-2 rounded-lg hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* User Info */}
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${getRoleColor()}`}>
                  {getUserIcon()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {user?.first_name} {user?.last_name}
                  </p>
                  <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                  <p className={`text-xs font-medium capitalize ${getRoleColor().split(' ')[0]}`}>
                    {user?.role}
                  </p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
              {getFilteredNavigationItems().map((item) => (
                <motion.button
                  key={item.id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleNavigation(item.path)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 text-left rounded-lg transition-colors ${
                    isActiveRoute(item.path)
                      ? 'bg-blue-50 text-blue-700 border border-blue-200'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <item.icon className={`w-5 h-5 ${
                    isActiveRoute(item.path) ? 'text-blue-600' : 'text-gray-500'
                  }`} />
                  <span className="font-medium">{item.label}</span>
                  {item.badge && (
                    <span className="ml-auto bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </motion.button>
              ))}
            </nav>

            {/* Sidebar Footer */}
            <div className="p-4 border-t border-gray-200">
              <div className="space-y-2">
                <button
                  onClick={() => handleNavigation('/profile')}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <User className="w-4 h-4" />
                  <span>Profile</span>
                </button>
                <button
                  onClick={() => handleNavigation('/settings')}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <Settings className="w-4 h-4" />
                  <span>Settings</span>
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Overlay for mobile */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsSidebarOpen(false)}
            className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          />
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Top Bar */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {navigationItems.find(item => isActiveRoute(item.path))?.label || 'DocTalk AI'}
              </h2>
              <p className="text-sm text-gray-600">
                Welcome back, {user?.first_name}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Role Badge */}
            <div className={`px-3 py-1 rounded-full text-xs font-medium ${getRoleColor()}`}>
              {user?.role}
            </div>
            
            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100"
              >
                <div className={`p-1 rounded-lg ${getRoleColor()}`}>
                  {getUserIcon()}
                </div>
                <span className="hidden md:block text-sm font-medium text-gray-700">
                  {user?.first_name}
                </span>
              </button>

              <AnimatePresence>
                {showUserMenu && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: -10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -10 }}
                    className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50"
                  >
                    <button
                      onClick={() => {
                        handleNavigation('/profile');
                        setShowUserMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                    >
                      <User className="w-4 h-4" />
                      <span>Profile</span>
                    </button>
                    <button
                      onClick={() => {
                        handleNavigation('/settings');
                        setShowUserMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                    >
                      <Settings className="w-4 h-4" />
                      <span>Settings</span>
                    </button>
                    <hr className="my-1" />
                    <button
                      onClick={() => {
                        handleLogout();
                        setShowUserMenu(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Sign Out</span>
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            
            <div className="text-sm text-gray-500">
              {new Date().toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
};

export default Layout;