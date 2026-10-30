import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { InstituteLayout } from './components/InstituteLayout';
import { DashboardPage } from './pages/institute/DashboardPage';
import { CertificatesPage } from './pages/institute/CertificatesPage';
import { ApplicationsPage } from './pages/institute/ApplicationsPage';
import { RulesPage } from './pages/institute/RulesPage';
import { UploadPage } from './pages/institute/UploadPage';
import { ValidationPage } from './pages/institute/ValidationPage';
import { ComplaintsPage } from './pages/institute/ComplaintsPage';
import { ReportsPage } from './pages/institute/ReportsPage';
import { AdminDashboard } from './pages/AdminDashboard';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

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
              <Route path="certificates" element={<CertificatesPage />} />
              <Route path="applications" element={<ApplicationsPage />} />
              <Route path="rules" element={<RulesPage />} />
              <Route path="upload" element={<UploadPage />} />
              <Route path="validation" element={<ValidationPage />} />
              <Route path="complaints" element={<ComplaintsPage />} />
              <Route path="reports" element={<ReportsPage />} />
            </Route>

            {/* Admin Portal Protected Route */}
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'REVIEWER']}>
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
