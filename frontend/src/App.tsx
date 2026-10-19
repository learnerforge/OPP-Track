import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import type { JSX } from 'react';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { ToastProvider } from '@/components/Toast';
import { Landing } from '@/pages/Landing';
import { Auth } from '@/pages/Auth';
import { Dashboard } from '@/pages/Dashboard';
import { Skeleton } from '@/components/ui/skeleton';

/** Gate for authenticated-only routes. Shows a loading state until the
 *  restored session is known, then redirects to /auth if signed out. */
function RequireAuth({ children }: { children: JSX.Element }) {
  const { session, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-paper p-6">
        <div className="mx-auto max-w-6xl space-y-4 pt-10">
          <Skeleton className="h-16" />
          <Skeleton className="h-40" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/auth" replace state={{ from: location.pathname }} />;
  }

  return children;
}

/** Signed-in users skip the auth page and land on the dashboard. */
function RedirectIfAuthed({ children }: { children: JSX.Element }) {
  const { session, loading } = useAuth();

  if (loading) return null;
  if (session) return <Navigate to="/dashboard" replace />;

  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route
              path="/auth"
              element={
                <RedirectIfAuthed>
                  <Auth />
                </RedirectIfAuthed>
              }
            />
            <Route
              path="/dashboard"
              element={
                <RequireAuth>
                  <Dashboard />
                </RequireAuth>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
