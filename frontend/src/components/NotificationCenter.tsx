import React, { useState, useRef, useEffect } from 'react';
import { useNotifications } from '../context/NotificationContext';
import { Bell, Info, AlertTriangle, FileCheck, CheckSquare } from 'lucide-react';

export const NotificationCenter: React.FC = () => {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const getIcon = (type: string) => {
    switch (type) {
      case 'ALERT':
        return <AlertTriangle className="w-4 h-4 text-brand-red" />;
      case 'VERIFICATION':
        return <FileCheck className="w-4 h-4 text-brand-blue" />;
      case 'CLAIM':
        return <CheckSquare className="w-4 h-4 text-brand-green" />;
      default:
        return <Info className="w-4 h-4 text-brand-sage" />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded hover:bg-brand-stone transition-all duration-150 cursor-pointer"
        aria-label="Notification Center"
      >
        <Bell className="w-5 h-5 text-brand-charcoal" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-brand-red rounded-full ring-2 ring-brand-ivory animate-pulse"></span>
        )}
      </button>

      {/* Notifications Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-white border border-brand-stone-dark rounded shadow-lg z-50">
          <div className="flex justify-between items-center px-4 py-3 border-b border-brand-stone-dark bg-brand-stone-light">
            <span className="font-display font-semibold text-sm">Alerts & Status Updates</span>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-[10px] text-brand-green font-semibold hover:underline cursor-pointer uppercase tracking-wider"
              >
                Mark all read
              </button>
            )}
          </div>
          
          <div className="divide-y divide-brand-stone-dark/30">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-xs text-brand-stone-dark font-medium">
                No notification alerts received.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => !n.is_read && markAsRead(n.id)}
                  className={`flex gap-3 p-4 hover:bg-brand-stone/30 transition cursor-pointer ${
                    !n.is_read ? 'bg-brand-green/5' : ''
                  }`}
                >
                  <div className="mt-0.5 flex-shrink-0">{getIcon(n.notification_type)}</div>
                  <div className="flex-1 flex flex-col gap-0.5">
                    <span className={`text-xs font-semibold ${!n.is_read ? 'text-brand-charcoal' : 'text-brand-charcoal/80'}`}>
                      {n.title}
                    </span>
                    <p className="text-[11px] text-brand-charcoal/70 leading-relaxed">
                      {n.message}
                    </p>
                    <span className="text-[9px] text-brand-stone-dark font-medium mt-1">
                      {new Date(n.created_at).toLocaleString()}
                    </span>
                  </div>
                  {!n.is_read && (
                    <div className="w-1.5 h-1.5 bg-brand-green rounded-full self-center flex-shrink-0"></div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
