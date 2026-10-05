// Layout.jsx — THE SHARED FRAME AROUND EVERY PAGE (except Login).
// It draws the navbar at the top, then shows the current page underneath.
// Change the navbar here once, and every page updates.

import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import { roleLabel } from "../auth/roles.js";

// The navbar links for each role. Each user only sees their own role's links.
// When a teammate adds a page, they add its link here under the right role.
const LINKS_BY_ROLE = {
  student: [{ to: "/student", label: "Dashboard" }],
  faculty: [{ to: "/faculty", label: "Dashboard" }],
  program_director: [{ to: "/program_director", label: "Dashboard" }],
};

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ---------- The navbar (top bar) ---------- */}
      <nav className="flex items-center gap-6 border-b bg-white px-6 py-3">
        <span className="font-bold text-indigo-700">GradTrack</span>

        {/* Only the links for this user's role. */}
        {LINKS_BY_ROLE[user.role].map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            // Highlight the link of the page we are currently on.
            className={({ isActive }) =>
              isActive ? "font-medium text-indigo-700" : "text-gray-600"
            }
          >
            {l.label}
          </NavLink>
        ))}

        {/* Right side: who is logged in + log out button. "ml-auto" pushes it to the right. */}
        <div className="ml-auto flex items-center gap-3 text-sm">
          <span className="text-gray-700">
            {user.full_name} <span className="text-gray-400">({roleLabel(user.role)})</span>
          </span>
          <button onClick={handleLogout} className="rounded border px-3 py-1 hover:bg-gray-100">
            Log out
          </button>
        </div>
      </nav>

      {/* ---------- The current page ---------- */}
      {/* <Outlet /> is a placeholder: React Router puts the matching page here
          (for example StudentDashboard when the URL is /student). */}
      <main className="mx-auto max-w-5xl p-6">
        <Outlet />
      </main>
    </div>
  );
}
