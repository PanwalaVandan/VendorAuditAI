import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout, AuthLayout } from '@/components/layout';
import { Landing, Login, Register, Dashboard, Vendors, VendorDetail, Documents, Query, Analysis, Remediation, Monitoring, Agents, Risk, Analytics, Competition, Playbooks, ApprovedVendors, BPO, Integrations, Frameworks } from '@/pages';
import { useAuthStore } from '@/stores/authStore';
import { ToastProvider } from '@/components/ui/toast';

/**
 * Protected Route wrapper - redirects to login if not authenticated
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/**
 * Public Route wrapper - redirects to dashboard if already authenticated
 */
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

function App() {
  const { init } = useAuthStore();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Run init synchronously then allow routes to render.
    // This prevents a race where Zustand's persisted isAuthenticated: true
    // is visible to ProtectedRoute/PublicRoute before init() has a chance
    // to reset it when tokens are missing (which causes the redirect loop).
    init();
    setReady(true);
  }, [init]);

  if (!ready) {
    // Blank frame while auth state is being resolved - avoids redirect flicker
    return null;
  }

  return (
    <ToastProvider>
      <div className="min-h-screen bg-background font-sans antialiased">
        <Routes>
        {/* Public routes (auth) */}
        <Route
          element={
            <PublicRoute>
              <AuthLayout />
            </PublicRoute>
          }
        >
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>

        {/* Protected routes (app) */}
        <Route
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/vendors" element={<Vendors />} />
          <Route path="/vendors/:id" element={<VendorDetail />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/query" element={<Query />} />
          <Route path="/analysis" element={<Analysis />} />
          <Route path="/remediation" element={<Remediation />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/playbooks" element={<Playbooks />} />
          <Route path="/approved-vendors" element={<ApprovedVendors />} />
          <Route path="/bpo" element={<BPO />} />
          <Route path="/integrations" element={<Integrations />} />
          <Route path="/frameworks" element={<Frameworks />} />
          <Route path="/search" element={<Dashboard />} />
          <Route path="/settings" element={<Dashboard />} />
        </Route>

        {/* Landing page */}
        <Route path="/" element={<Landing />} />

        {/* Public Competition page (marketing) */}
        <Route path="/competition" element={<Competition />} />

        {/* Catch all - redirect to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </ToastProvider>
  );
}

export default App;
