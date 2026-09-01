import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { BusinessProvider, useBusiness } from './context/BusinessContext';
import { NotificationProvider, useNotifications } from './context/NotificationContext';
import MainLayout from './components/layout/MainLayout';

// Pages
import DashboardPage from './pages/DashboardPage';
import CommandCenterPage from './pages/CommandCenterPage';
import ExceptionCenterPage from './pages/ExceptionCenterPage';
import WorkflowBuilderPage from './pages/WorkflowBuilderPage';
import DocumentsPage from './pages/DocumentsPage';
import InvoicesPage from './pages/InvoicesPage';
import CustomersPage from './pages/CustomersPage';
import TasksPage from './pages/TasksPage';
import ApprovalsPage from './pages/ApprovalsPage';
import EmailAssistantPage from './pages/EmailAssistantPage';
import MessageCenterPage from './pages/MessageCenterPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ActivityLogPage from './pages/ActivityLogPage';
import SettingsPage from './pages/SettingsPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

import api from './services/api';

const AppContent = () => {
  const { user, token, loading: authLoading } = useAuth();
  const [authView, setAuthView] = useState('login'); // 'login' or 'register'
  const [activeTab, setActiveTab] = useState('dashboard');
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);

  // Periodic check for pending approvals badge (only when authenticated)
  useEffect(() => {
    if (!token && !user) {
      setPendingApprovalsCount(0);
      return;
    }

    const fetchPendingApprovals = async () => {
      try {
        const res = await api.get('/approvals?status=pending');
        setPendingApprovalsCount(res.data?.length || 0);
      } catch (err) {
        // silent catch
      }
    };

    fetchPendingApprovals();
    const interval = setInterval(fetchPendingApprovals, 10000);
    return () => clearInterval(interval);
  }, [activeTab, token, user]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0b0f19] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
          <span className="text-xs text-slate-400">Initializing AI Business Platform...</span>
        </div>
      </div>
    );
  }

  // If unauthenticated, show Login or Register page
  if (!user && !token) {
    if (authView === 'register') {
      return <RegisterPage onSwitchToLogin={() => setAuthView('login')} />;
    }
    return <LoginPage onSwitchToRegister={() => setAuthView('register')} />;
  }

  const [navParams, setNavParams] = useState({});

  const handleNavigate = (tab, params = {}) => {
    setNavParams(params || {});
    setActiveTab(tab);
  };

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardPage onNavigate={handleNavigate} />;
      case 'command_center':
        return <CommandCenterPage onNavigate={handleNavigate} />;
      case 'exceptions':
        return <ExceptionCenterPage onNavigate={handleNavigate} />;
      case 'workflows':
        return <WorkflowBuilderPage onNavigate={handleNavigate} />;
      case 'documents':
        return <DocumentsPage onNavigate={handleNavigate} />;
      case 'invoices':
        return <InvoicesPage onNavigate={handleNavigate} />;
      case 'customers':
        return <CustomersPage onNavigate={handleNavigate} />;
      case 'tasks':
        return <TasksPage onNavigate={handleNavigate} />;
      case 'approvals':
        return <ApprovalsPage onNavigate={handleNavigate} />;
      case 'email_assistant':
        return <EmailAssistantPage onNavigate={handleNavigate} />;
      case 'message_center':
        return (
          <MessageCenterPage
            onNavigate={handleNavigate}
            preSelectedCustomerId={navParams.customerId || null}
          />
        );
      case 'analytics':
        return <AnalyticsPage onNavigate={handleNavigate} />;
      case 'activity':
        return <ActivityLogPage onNavigate={handleNavigate} />;
      case 'settings':
        return <SettingsPage onNavigate={handleNavigate} />;
      default:
        return <DashboardPage onNavigate={handleNavigate} />;
    }
  };

  return (
    <MainLayout
      activeTab={activeTab}
      setActiveTab={(tab) => handleNavigate(tab, {})}
      pendingApprovalsCount={pendingApprovalsCount}
    >
      {renderActivePage()}
    </MainLayout>
  );
};

function App() {
  return (
    <AuthProvider>
      <BusinessProvider>
        <NotificationProvider>
          <AppContent />
        </NotificationProvider>
      </BusinessProvider>
    </AuthProvider>
  );
}

export default App;
