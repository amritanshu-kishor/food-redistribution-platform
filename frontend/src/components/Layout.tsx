import React from 'react';
import { useAuth } from '../context/AuthContext';
import { navigateTo } from '../services/router';
import { NotificationCenter } from './NotificationCenter';
import { 
  LayoutDashboard, PlusCircle, Search, History, BarChart3, 
  Users, ShieldCheck, AlertCircle, Terminal, Download, LogOut, User as UserIcon
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  activePath: string;
}

export const Layout: React.FC<LayoutProps> = ({ children, activePath }) => {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigateTo('/login');
  };

  const getSidebarLinks = () => {
    if (!user) return [];

    switch (user.role) {
      case 'restaurant':
        return [
          { name: 'Dashboard', path: '/restaurant', icon: <LayoutDashboard className="w-4 h-4" /> },
          { name: 'Post Donation', path: '/restaurant/create', icon: <PlusCircle className="w-4 h-4" /> },
          { name: 'Active Listing', path: '/restaurant/donations', icon: <Search className="w-4 h-4" /> },
          { name: 'Claim History', path: '/restaurant/history', icon: <History className="w-4 h-4" /> },
          { name: 'Impact Analytics', path: '/restaurant/analytics', icon: <BarChart3 className="w-4 h-4" /> },
        ];
      case 'ngo':
        return [
          { name: 'Dashboard', path: '/ngo', icon: <LayoutDashboard className="w-4 h-4" /> },
          { name: 'Browse Foods', path: '/ngo/browse', icon: <Search className="w-4 h-4" /> },
          { name: 'My Claims', path: '/ngo/claims', icon: <PlusCircle className="w-4 h-4" /> },
          { name: 'Donation History', path: '/ngo/history', icon: <History className="w-4 h-4" /> },
          { name: 'Impact Analytics', path: '/ngo/analytics', icon: <BarChart3 className="w-4 h-4" /> },
        ];
      case 'admin':
        return [
          { name: 'Dashboard', path: '/admin', icon: <LayoutDashboard className="w-4 h-4" /> },
          { name: 'User Management', path: '/admin/users', icon: <Users className="w-4 h-4" /> },
          { name: 'Verifications', path: '/admin/verifications', icon: <ShieldCheck className="w-4 h-4" /> },
          { name: 'Complaints', path: '/admin/complaints', icon: <AlertCircle className="w-4 h-4" /> },
          { name: 'Security Audit', path: '/admin/audit', icon: <Terminal className="w-4 h-4" /> },
          { name: 'Impact Reports', path: '/admin/reports', icon: <Download className="w-4 h-4" /> },
        ];
      default:
        return [];
    }
  };

  const renderStatusBanner = () => {
    if (!user || user.role === 'admin') return null;

    if (user.status === 'pending') {
      return (
        <div className="bg-brand-amber/12 border-b border-brand-amber/25 text-brand-amber text-xs px-6 py-3 font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>
            Your account is <strong>pending verification</strong>. An admin must approve your organisation before you can post or claim food.
            Log in as <strong>admin@foodshare.io</strong> and open Verifications.
          </span>
        </div>
      );
    }

    if (user.status === 'suspended') {
      return (
        <div className="bg-brand-red/10 border-b border-brand-red/30 text-brand-red text-xs px-6 py-3 font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>Your account has been <strong>suspended</strong>. Contact administration.</span>
        </div>
      );
    }

    if (user.status === 'rejected') {
      return (
        <div className="bg-brand-red/10 border-b border-brand-red/30 text-brand-red text-xs px-6 py-3 font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>Verification was <strong>rejected</strong>. Upload valid documents and wait for another review.</span>
        </div>
      );
    }

    return null;
  };

  const links = getSidebarLinks();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 flex justify-between items-center px-6 py-3 bg-brand-ivory/80 backdrop-blur-md border-b border-brand-stone-dark/40">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigateTo(user ? `/${user.role}` : '/')}>
          <div className="w-9 h-9 rounded-2xl bg-brand-pine text-brand-ivory font-display font-bold text-lg flex items-center justify-center">
            H
          </div>
          <span className="font-display font-bold text-lg tracking-tight">Harvest Link</span>
        </div>

        <div className="flex items-center gap-4">
          <NotificationCenter />
          <div className="h-5 w-px bg-brand-stone-dark/70" />
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-brand-green text-brand-ivory flex items-center justify-center">
              <UserIcon className="w-4 h-4" />
            </div>
            <div className="flex flex-col text-left">
              <span className="text-xs font-semibold leading-tight">{user?.full_name}</span>
              <span className="text-[10px] text-brand-amber uppercase tracking-wider font-semibold">{user?.role}</span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-full text-brand-charcoal/50 hover:text-brand-red hover:bg-brand-red/10 cursor-pointer"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {renderStatusBanner()}

      <div className="flex-1 flex">
        <aside className="w-64 m-4 mr-0 rounded-[1.8rem] bg-brand-pine text-brand-ivory p-5 hidden md:flex flex-col gap-6">
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] text-brand-ivory/40 font-bold uppercase tracking-widest pl-2">Navigation</span>
            <nav className="flex flex-col gap-1">
              {links.map((link) => {
                const isActive = activePath === link.path;
                return (
                  <button
                    key={link.path}
                    onClick={() => navigateTo(link.path)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-2xl text-xs font-semibold text-left cursor-pointer ${
                      isActive
                        ? 'bg-brand-amber text-white'
                        : 'text-brand-ivory/75 hover:bg-white/10'
                    }`}
                  >
                    {link.icon}
                    <span>{link.name}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {user?.organization && (
            <div className="mt-auto rounded-2xl p-4 bg-white/8 border border-white/10">
              <span className="text-[9px] text-brand-ivory/45 uppercase tracking-wider font-bold">Organisation</span>
              <span className="block text-xs font-bold leading-tight mt-1">{user.organization.name}</span>
              <div className="flex items-center gap-1.5 mt-2">
                <span className={`w-1.5 h-1.5 rounded-full ${user.organization.is_verified ? 'bg-brand-gold' : 'bg-brand-amber'}`} />
                <span className="text-[10px] font-semibold text-brand-ivory/70">
                  {user.organization.is_verified ? 'Verified partner' : 'Pending verification'}
                </span>
              </div>
            </div>
          )}
        </aside>

        <main className="flex-1 p-6 md:p-10 overflow-y-auto">
          <div className="max-w-6xl mx-auto flex flex-col gap-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
