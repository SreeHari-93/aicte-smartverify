import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { InstituteLayout } from './components/InstituteLayout';
import { DashboardPage } from './pages/institute/DashboardPage';
import { ApplicationsPage } from './pages/institute/ApplicationsPage';
import { UploadPage } from './pages/institute/UploadPage';
import { ComplaintsPage } from './pages/institute/ComplaintsPage';
import { ReportsPage } from './pages/institute/ReportsPage';
import { InstituteUndertakingsPage } from './pages/institute/InstituteUndertakingsPage';
import { InstituteNotificationsPage } from './pages/institute/InstituteNotificationsPage';
import { InstituteDocumentValidityPage } from './pages/institute/InstituteDocumentValidityPage';
import { AdminDashboard } from './pages/AdminDashboard';
import { AdminLayout } from './components/AdminLayout';
import { AdminWorkflowPage } from './pages/admin/AdminWorkflowPage';
import { AdminApplicationsPage } from './pages/admin/AdminApplicationsPage';
import { AdminEvcPage } from './pages/admin/AdminEvcPage';
import { AdminUndertakingsPage } from './pages/admin/AdminUndertakingsPage';
import { AdminDocumentValidityPage } from './pages/admin/AdminDocumentValidityPage';
import { AdminAlertsPage } from './pages/admin/AdminAlertsPage';
import { AdminRulesPage } from './pages/admin/AdminRulesPage';
import { AdminAuditLogPage } from './pages/admin/AdminAuditLogPage';
import { AdminReportsPage } from './pages/admin/AdminReportsPage';
import { AdminComplaintsInboxPage } from './pages/admin/AdminComplaintsInboxPage';
import { AdminEvaluationPage } from './pages/admin/AdminEvaluationPage';
import { AdminCoveragePage } from './pages/admin/AdminCoveragePage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const ADMIN_ALLOWED_ROLES = [
  'ADMIN',
  'REVIEWER',
  'REGIONAL_OFFICER',
  'BUREAU_OFFICER',
  'COMMITTEE_MEMBER',
];

// Protected Route Guard
const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  allowedRoles?: string[];
}> = ({ children, allowedRoles }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-[#0B3C9D] border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-600 font-medium">Verifying AICTE Session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <Navigate
        to={user.role === 'INSTITUTE' ? '/institute/dashboard' : '/admin/dashboard'}
        replace
      />
    );
  }

  return <>{children}</>;
};

// Route Guard: Committee members can only view Dashboard, EVC, Applications (assigned only), and Alerts
const CommitteeRestrictedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  if (user?.role === 'COMMITTEE_MEMBER') {
    return <Navigate to="/admin/dashboard" replace />;
  }
  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Institute Portal Protected Routes with Shared Layout */}
            <Route
              path="/institute"
              element={
                <ProtectedRoute allowedRoles={['INSTITUTE']}>
                  <InstituteLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/institute/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="applications" element={<ApplicationsPage />} />
              <Route path="undertakings" element={<InstituteUndertakingsPage />} />
              <Route path="validity" element={<InstituteDocumentValidityPage />} />
              <Route path="certificates" element={<InstituteDocumentValidityPage />} />
              <Route path="upload" element={<UploadPage />} />
              <Route path="complaints" element={<ComplaintsPage />} />
              <Route path="notifications" element={<InstituteNotificationsPage />} />
              <Route path="reports" element={<ReportsPage />} />

              {/* Removed / Unneeded routes safely redirected */}
              <Route path="infrastructure" element={<Navigate to="/institute/dashboard" replace />} />
              <Route path="validation" element={<Navigate to="/institute/dashboard" replace />} />
              <Route path="rules" element={<Navigate to="/institute/dashboard" replace />} />
            </Route>

            {/* Admin Portal Protected Routes with Shared Admin Layout */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute allowedRoles={ADMIN_ALLOWED_ROLES}>
                  <AdminLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="dashboard" element={<AdminDashboard />} />

              {/* Committee members can access EVC, Applications, Alerts */}
              <Route path="applications" element={<AdminApplicationsPage />} />
              <Route path="evc" element={<AdminEvcPage />} />
              <Route path="alerts" element={<AdminAlertsPage />} />

              {/* Committee-restricted governance routes */}
              <Route
                path="workflow"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminWorkflowPage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="undertakings"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminUndertakingsPage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="validity"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminDocumentValidityPage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="document-validity"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminDocumentValidityPage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="rules"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminRulesPage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="complaints"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminComplaintsInboxPage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="reports"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminReportsPage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="evaluation"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminEvaluationPage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="coverage"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminCoveragePage />
                  </CommitteeRestrictedRoute>
                }
              />
              <Route
                path="audit-log"
                element={
                  <CommitteeRestrictedRoute>
                    <AdminAuditLogPage />
                  </CommitteeRestrictedRoute>
                }
              />

              {/* Merged / Redirected routes */}
              <Route path="document-types" element={<Navigate to="/admin/rules?tab=types" replace />} />
              <Route path="checklists" element={<Navigate to="/admin/rules?tab=checklists" replace />} />

              {/* Removed routes redirected to admin dashboard */}
              <Route path="verification" element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="verification-queue" element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="anomalies" element={<Navigate to="/admin/dashboard" replace />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
