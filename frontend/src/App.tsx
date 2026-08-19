import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { useCurrentPath, navigateTo } from './services/router';
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { RestaurantPortal } from './pages/RestaurantPortal';
import { NGOPortal } from './pages/NGOPortal';
import { AdminPortal } from './pages/AdminPortal';

const AppContent: React.FC = () => {
  const currentPath = useCurrentPath();
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col justify-center items-center font-sans">
        <div className="flex flex-col items-center gap-3">
          <div className="w-11 h-11 rounded-full border-2 border-brand-stone-dark border-t-brand-amber animate-spin"></div>
          <span className="text-[10px] font-bold text-brand-charcoal/50 tracking-widest uppercase">
            Setting the table
          </span>
        </div>
      </div>
    );
  }

  // Public Route Switchboard
  if (currentPath === '/' || currentPath === '') {
    return <Landing />;
  }

  if (currentPath === '/login') {
    return <Login />;
  }

  if (currentPath === '/register') {
    return <Register />;
  }

  // Security Access Guard: Logged out users are forced to authenticate
  if (!user) {
    // Prevent infinite redirect loop if already going to login
    setTimeout(() => navigateTo('/login'), 50);
    return null;
  }

  // Dashboard Role Access Switchboard
  if (currentPath.startsWith('/restaurant')) {
    if (user.role !== 'restaurant') {
      navigateTo(`/${user.role}`);
      return null;
    }
    return <RestaurantPortal path={currentPath} />;
  }

  if (currentPath.startsWith('/ngo')) {
    if (user.role !== 'ngo') {
      navigateTo(`/${user.role}`);
      return null;
    }
    return <NGOPortal path={currentPath} />;
  }

  if (currentPath.startsWith('/admin')) {
    if (user.role !== 'admin') {
      navigateTo(`/${user.role}`);
      return null;
    }
    return <AdminPortal path={currentPath} />;
  }

  // 404 Fallback
  return (
    <div className="min-h-screen flex flex-col justify-center items-center text-center font-sans p-6">
      <span className="text-xs font-bold text-brand-red uppercase tracking-widest bg-brand-red/10 px-3 py-1 rounded-full">
        Error 404
      </span>
      <h1 className="text-2xl font-bold mt-3 text-brand-charcoal">Resource Not Found</h1>
      <p className="text-xs text-brand-charcoal/70 max-w-xs mt-1 leading-relaxed">
        The path you are looking for does not exist or you lack administrative privileges.
      </p>
      <button 
        onClick={() => navigateTo(user ? `/${user.role}` : '/')} 
        className="btn-tactile text-xs mt-6 px-5 py-2 uppercase tracking-wider font-bold"
      >
        Return Dashboard
      </button>
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <AppContent />
      </NotificationProvider>
    </AuthProvider>
  );
}
