import React from 'react';
import {
  LayoutDashboard,
  Bot,
  FileText,
  Receipt,
  Users,
  CheckSquare,
  ShieldCheck,
  Mail,
  MessageSquare,
  BarChart3,
  History,
  Settings,
  Sparkles,
  AlertTriangle,
  Workflow
} from 'lucide-react';
import { useBusiness } from '../../context/BusinessContext';

const Sidebar = ({ activeTab, setActiveTab, isOpen, setIsOpen, pendingApprovalsCount = 0 }) => {
  const { business } = useBusiness();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'command_center', label: 'Command Center', icon: Bot },
    { id: 'exceptions', label: 'Exception Center', icon: AlertTriangle },
    { id: 'workflows', label: 'AI Workflows', icon: Workflow },
    { id: 'documents', label: 'Documents & OCR', icon: FileText },
    { id: 'invoices', label: 'Invoices & Billing', icon: Receipt },
    { id: 'customers', label: 'Customers', icon: Users },
    { id: 'tasks', label: 'Tasks & Operations', icon: CheckSquare },
    { id: 'approvals', label: 'Approval Center', icon: ShieldCheck, badge: pendingApprovalsCount },
    { id: 'email_assistant', label: 'Email Sender', icon: Mail },
    { id: 'message_center', label: 'Message Center', icon: MessageSquare },
    { id: 'analytics', label: 'Analytics & Reports', icon: BarChart3 },
    { id: 'activity', label: 'Dispatched Logs', icon: History },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-white dark:bg-[#0f0f12] border-r border-slate-200 dark:border-[#222227] flex flex-col transition-all duration-200 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-200 dark:border-[#222227] bg-white dark:bg-[#0f0f12]">
          <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center shadow-xs">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div className="flex flex-col min-w-0">
            <h1 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight truncate leading-none">
              AI Business Agent
            </h1>
            <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium tracking-wide mt-1 truncate">
              {business?.name || 'Operations Platform'}
            </span>
          </div>
        </div>

        {/* Navigation items */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
            Operations
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  if (window.innerWidth < 1024) setIsOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-2xs dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/30'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-[#18181d] border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      isActive
                        ? 'text-indigo-600 dark:text-indigo-400'
                        : 'text-slate-400 dark:text-slate-500'
                    }`}
                  />
                  <span className="truncate">{item.label}</span>
                </div>

                {item.badge > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-rose-500 text-white shadow-xs">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* System status footer */}
        <div className="p-3.5 border-t border-slate-200 dark:border-[#222227] bg-slate-50 dark:bg-[#121216]">
          <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="font-medium">AI Operations Active</span>
            </div>
            <span className="font-mono text-[10px] text-slate-400">v1.0</span>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
