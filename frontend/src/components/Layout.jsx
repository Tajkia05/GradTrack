// Layout.jsx — THE SHARED FRAME AROUND EVERY PAGE (except Login).
// It draws the navbar at the top, then shows the current page underneath.
// Change the navbar here once, and every page updates.

import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import { roleLabel } from "../auth/roles.js";
import logoMark from "../assets/gradtrack-mark.png";

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
    <div className="min-h-screen bg-ink text-mist">
      {/* ---------- The navbar (top bar) ---------- */}
      <nav className="border-b border-line bg-ink/80">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          {/* The logo: graduation cap + name. */}
          <span className="flex items-center gap-2 font-display text-lg font-bold text-white">
            <img src={logoMark} alt="" className="h-7 w-auto" />
            GradTrack
          </span>

          {/* Only the links for this user's role. */}
          {LINKS_BY_ROLE[user.role].map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              // Highlight the link of the page we are currently on.
              className={({ isActive }) =>
                "text-sm transition-colors " + (isActive ? "font-medium text-sage" : "text-mist/70 hover:text-white")
              }
            >
              {l.label}
            </NavLink>
          ))}

          {/* Right side: who is logged in + log out button. "ml-auto" pushes it to the right. */}
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="text-mist">
              {user.full_name} <span className="text-mist/50">({roleLabel(user.role)})</span>
            </span>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-line px-3 py-1 text-mist transition-colors hover:border-sage hover:text-white"
            >
              Log out
            </button>
          </div>
        </div>
      </nav>

      {/* ---------- The current page ---------- */}
      {/* <Outlet /> is a placeholder: React Router puts the matching page here
          (for example StudentDashboard when the URL is /student). */}
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
