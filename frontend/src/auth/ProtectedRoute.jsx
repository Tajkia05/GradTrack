// ProtectedRoute.jsx — THE "BOUNCER" FOR PAGES.
// Wrap routes with it in App.jsx to decide who may see them:
//
//   <Route element={<ProtectedRoute />}>                 → any logged-in user
//   <Route element={<ProtectedRoute role="student" />}>  → only students
//
// What it does:
//   not logged in            → send to /login
//   logged in, wrong role    → send to their OWN dashboard
//   allowed                  → show the page
//
// NOTE: this only hides pages in the browser. The real protection is on the
// backend (require_role in core/deps.py), because people can call the API directly.

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

export default function ProtectedRoute({ role }) {
  const { user, loading } = useAuth();

  // Still checking the saved token — don't redirect yet.
  if (loading) return <p className="p-6 text-gray-500">Loading...</p>;

  if (!user) return <Navigate to="/login" replace />;

  if (role && user.role !== role) return <Navigate to={`/${user.role}`} replace />;

  // <Outlet /> = "show whatever page is inside me".
  return <Outlet />;
}
