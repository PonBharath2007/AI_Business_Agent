import React, { useState, useEffect, lazy, Suspense } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { BusinessProvider } from './context/BusinessContext';
import { NotificationProvider } from './context/NotificationContext';
import { ThemeProvider } from './context/ThemeContext';
import MainLayout from './components/layout/MainLayout';
import api from './services/api';

// Core pages (loaded directly for instant first paint)
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

// Lazy-loaded heavy modules (code-split to optimize bundle size and speed)
const CommandCenterPage = lazy(() => import('./pages/CommandCenterPage'));
const ExceptionCenterPage = lazy(() => import('./pages/ExceptionCenterPage'));
const WorkflowBuilderPage = lazy(() => import('./pages/WorkflowBuilderPage'));
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'));
const InvoicesPage = lazy(() => import('./pages/InvoicesPage'));
const CustomersPage = lazy(() => import('./pages/CustomersPage'));
const TasksPage = lazy(() => import('./pages/TasksPage'));
const ApprovalsPage = lazy(() => import('./pages/ApprovalsPage'));
const EmailAssistantPage = lazy(() => import('./pages/EmailAssistantPage'));
const MessageCenterPage = lazy(() => import('./pages/MessageCenterPage'));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'));
const ActivityLogPage = lazy(() => import('./pages/ActivityLogPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));

const PageFallback = () => (
  <div className="flex flex-col items-center justify-center min-h-[40vh] space-y-3">
    <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
    <span className="text-xs text-slate-500">Loading module...</span>
  </div>
);

const AppContent = () => {
  const { user, token, loading: authLoading } = useAuth();
  const [authView, setAuthView] = useState('login'); // 'login' or 'register'
  const [activeTab, setActiveTab] = useState('dashboard');
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);
  const [navParams, setNavParams] = useState({});

  // Periodic check for pending approvals badge (only when authenticated, decoupled from activeTab)
  useEffect(() => {
    if (!token && !user) {
      setPendingApprovalsCount(0);
      return;
    }

    let isMounted = true;
    const fetchPendingApprovals = async () => {
      try {
        const res = await api.get('/approvals?status=pending');
        if (isMounted) {
          setPendingApprovalsCount(res.data?.length || 0);
        }
      } catch (err) {
        // silent catch
      }
    };

    fetchPendingApprovals();
    const interval = setInterval(fetchPendingApprovals, 30000); // 30s background check
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [token, user]);

  const handleNavigate = (tab, params = {}) => {
    setNavParams(params || {});
    setActiveTab(tab);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-[#0b0f19] flex items-center justify-center transition-colors">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 border-3 border-indigo-600/30 border-t-indigo-600 rounded-full animate-spin" />
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Initializing AI Business Platform...</span>
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
      <Suspense fallback={<PageFallback />}>
        {renderActivePage()}
      </Suspense>
    </MainLayout>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BusinessProvider>
          <NotificationProvider>
            <AppContent />
          </NotificationProvider>
        </BusinessProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
