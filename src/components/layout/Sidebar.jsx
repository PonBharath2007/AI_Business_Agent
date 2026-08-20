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
    { id: 'command_center', label: 'Command Center', icon: Bot, isAIFeature: false },
    { id: 'exceptions', label: 'Exception Center', icon: AlertTriangle, isAIFeature: true },
    { id: 'workflows', label: 'AI Workflows', icon: Workflow, isAIFeature: true },
    { id: 'documents', label: 'Documents & OCR', icon: FileText },
    { id: 'invoices', label: 'Invoices & Billing', icon: Receipt },
    { id: 'customers', label: 'Customers', icon: Users },
    { id: 'tasks', label: 'Tasks & Operations', icon: CheckSquare },
    { id: 'approvals', label: 'Approval Center', icon: ShieldCheck, badge: pendingApprovalsCount },
    { id: 'email_assistant', label: 'AI Email Studio', icon: Mail, isAIFeature: true },
    { id: 'analytics', label: 'Analytics & KPIs', icon: BarChart3 },
    { id: 'activity', label: 'Activity & Audit', icon: History },
    { id: 'settings', label: 'Business Profile', icon: Settings },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 glass-panel border-r border-slate-800 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 ${isOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-800 bg-slate-900/40">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md shadow-indigo-500/30">
            <Sparkles className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div className="flex flex-col min-w-0">
            <h1 className="text-sm font-bold text-white tracking-tight truncate leading-none">
              AI Ops Agent
            </h1>
            <span className="text-[10px] text-indigo-400 font-medium tracking-wide uppercase mt-1 truncate">
              {business?.name || 'Digital Employee'}
            </span>
          </div>
        </div>

        {/* Navigation items */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          <div className="px-3 pb-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Operations Platform
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
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 group ${isActive
                  ? 'bg-indigo-600/20 text-white border border-indigo-500/40 shadow-inner'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 border border-transparent'
                  }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-colors ${isActive
                      ? 'text-indigo-400'
                      : 'text-slate-400 group-hover:text-slate-200'
                      }`}
                  />
                  <span className="truncate">{item.label}</span>
                </div>

                <div className="flex items-center gap-1.5">
                  {item.isAIFeature && (
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      AI
                    </span>
                  )}
                  {item.badge > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500 text-white animate-pulse">
                      {item.badge}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Status Pill in Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <div className="flex flex-col">
              <span className="text-[11px] font-semibold text-emerald-300 leading-tight">AI Employee Active</span>
              <span className="text-[9px] text-slate-400">Autonomous Monitoring</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
