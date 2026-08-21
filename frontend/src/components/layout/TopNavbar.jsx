import React, { useState, useRef, useEffect } from 'react';
import {
  Menu,
  Bell,
  Sparkles,
  RotateCcw,
  User,
  LogOut,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Info
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useBusiness } from '../../context/BusinessContext';
import { useNotifications } from '../../context/NotificationContext';
import Button from '../common/Button';

const TopNavbar = ({ onMenuClick, onNavigate }) => {
  const { user, logout } = useAuth();
  const { business, resetDemoData, loading } = useBusiness();
  const { notifications, unreadCount, markAsRead, markAllRead } = useNotifications();

  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const notifRef = useRef(null);
  const userRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifications(false);
      }
      if (userRef.current && !userRef.current.contains(e.target)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleReset = async () => {
    if (window.confirm('Reset all demo data (ABC Ltd, Invoices, Tasks, Approvals) to initial pristine state?')) {
      await resetDemoData();
      window.location.reload();
    }
  };

  return (
    <header className="sticky top-0 z-30 h-16 glass-panel border-b border-slate-800 flex items-center justify-between px-4 sm:px-6 bg-slate-900/80 backdrop-blur-md">
      {/* Left section */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700/60">
          <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          <span className="text-xs font-medium text-slate-200 truncate max-w-[200px] md:max-w-none">
            {business?.name || 'Summit Digital Agency'}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold uppercase">
            {business?.currency || 'USD'}
          </span>
        </div>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2.5">
        {/* Quick Demo Data Reset Button */}
        <Button
          onClick={handleReset}
          variant="outline"
          size="sm"
          loading={loading}
          icon={RotateCcw}
          className="hidden sm:inline-flex text-xs text-slate-300 hover:border-indigo-500/50"
        >
          Reset Demo State
        </Button>

        {/* AI Command Center Quick trigger */}
        <Button
          onClick={() => onNavigate('command_center')}
          variant="primary"
          size="sm"
          icon={Sparkles}
          className="text-xs"
        >
          AI Agent
        </Button>

        {/* Notifications Popover */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl glass-panel border border-slate-700/80 shadow-2xl p-4 animate-in fade-in zoom-in-95 z-50">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-white">Notifications</h4>
                  {unreadCount > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 font-bold">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllRead}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="mt-3 max-h-72 overflow-y-auto space-y-2">
                {!notifications.length ? (
                  <div className="text-center py-6 text-xs text-slate-400">
                    No active notifications.
                  </div>
                ) : (
                  notifications.map((n) => {
                    let Icon = Info;
                    let color = 'text-sky-400 bg-sky-500/10';
                    if (n.priority === 'High') {
                      Icon = AlertTriangle;
                      color = 'text-rose-400 bg-rose-500/10';
                    }

                    return (
                      <div
                        key={n.id}
                        onClick={() => {
                          markAsRead(n.id);
                          if (n.action_url) {
                            const tab = n.action_url.replace('/', '');
                            onNavigate(tab || 'dashboard');
                            setShowNotifications(false);
                          }
                        }}
                        className={`p-3 rounded-xl border text-left transition-colors cursor-pointer ${
                          n.read
                            ? 'bg-slate-900/40 border-slate-800/60 opacity-70'
                            : 'bg-slate-800/80 border-slate-700 hover:border-indigo-500/40'
                        }`}
                      >
                        <div className="flex items-start gap-2.5">
                          <div className={`p-1.5 rounded-lg shrink-0 ${color}`}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h5 className="text-xs font-semibold text-slate-100 truncate">{n.title}</h5>
                            <p className="text-[11px] text-slate-300 mt-0.5 line-clamp-2">{n.message}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Menu */}
        <div className="relative" ref={userRef}>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-slate-800 transition-colors"
          >
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white font-bold text-xs shadow-md">
              {(user?.name || user?.email || 'U').charAt(0).toUpperCase()}
            </div>
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 rounded-2xl glass-panel border border-slate-700/80 shadow-2xl p-2 animate-in fade-in zoom-in-95 z-50">
              <div className="px-3 py-2 border-b border-slate-800">
                <p className="text-xs font-bold text-white truncate">{user?.name || 'Authenticated User'}</p>
                <p className="text-[11px] text-slate-400 truncate">{user?.email || ''}</p>
                {user?.business_name && (
                  <p className="text-[10px] text-indigo-400 font-medium truncate mt-0.5">{user.business_name}</p>
                )}
              </div>

              <div className="mt-1 space-y-1">
                <button
                  onClick={() => {
                    onNavigate('settings');
                    setShowUserMenu(false);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/80 rounded-xl"
                >
                  <User className="w-4 h-4 text-slate-400" />
                  Business Profile
                </button>
                <button
                  onClick={() => {
                    logout();
                    setShowUserMenu(false);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-xl"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default TopNavbar;
