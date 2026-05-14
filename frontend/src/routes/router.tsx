import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/features/auth/AuthProvider';
import { LoginPage } from '@/features/auth/LoginPage';
import { ProjectsPage } from '@/features/projects/ProjectsPage';
import { EditorPage } from '@/features/editor/EditorPage';

function RootLayout() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-6">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      {
        path: '/projects',
        element: (
          <Protected>
            <ProjectsPage />
          </Protected>
        ),
      },
      {
        path: '/projects/:projectId',
        element: (
          <Protected>
            <EditorPage />
          </Protected>
        ),
      },
      { path: '/', element: <Navigate to="/projects" replace /> },
    ],
  },
]);
