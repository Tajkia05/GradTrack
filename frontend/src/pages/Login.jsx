// Login.jsx — THE SIGN-IN PAGE. URL: /login
// Who uses it: everyone, before they get into the app.
//
// The user picks their role (Student / Faculty / Program Director), types email + password,
// we ask the backend → if correct, we send them to their own dashboard.

import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import RoleSelector from "../components/RoleSelector.jsx";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  // "State" = values that can change while the page is open.
  const [role, setRole] = useState("student");       // which role button is selected
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");            // error message to show in red
  const [submitting, setSubmitting] = useState(false); // true while waiting for the backend

  // Already logged in? Skip the login page and go straight to your dashboard.
  if (user) return <Navigate to={`/${user.role}`} replace />;

  // Runs when the "Sign in" button is clicked (or Enter is pressed).
  async function handleSubmit(e) {
    e.preventDefault(); // stop the browser from reloading the page
    setError("");
    setSubmitting(true);
    try {
      const loggedInUser = await login(email, password, role);
      navigate(`/${loggedInUser.role}`, { replace: true });
    } catch (err) {
      setError(err.message); // e.g. "Invalid email or password"
    } finally {
      setSubmitting(false);
    }
  }

  return (
    // The lamp screen around this card comes from components/AuthShell.jsx.
    <form onSubmit={handleSubmit} className="auth-card w-full rounded-2xl p-6">
      <h1 className="mb-5 font-display text-2xl font-bold text-white">Sign in</h1>

      {/* The three role buttons. */}
      <RoleSelector value={role} onChange={setRole} />

      <label className="mb-1 block text-sm font-medium text-mist" htmlFor="email">Email</label>
      <input
        id="email"
        type="email"
        required
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="mb-3 w-full rounded-lg border border-line bg-ink px-3 py-2 text-white outline-none transition focus:border-sage focus:ring-2 focus:ring-sage/30"
      />

      <label className="mb-1 block text-sm font-medium text-mist" htmlFor="password">Password</label>
      <input
        id="password"
        type="password"
        required
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="mb-3 w-full rounded-lg border border-line bg-ink px-3 py-2 text-white outline-none transition focus:border-sage focus:ring-2 focus:ring-sage/30"
      />

      {/* Only shown when login failed. */}
      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-sage py-2 font-semibold text-ink transition hover:bg-sage-light disabled:opacity-50"
      >
        {submitting ? "Signing in..." : "Sign in"}
      </button>

      {/* Link to the registration page. */}
      <p className="mt-4 text-center text-sm text-mist/70">
        New to GradTrack?{" "}
        <Link to="/register" className="font-medium text-sage hover:underline">
          Create an account
        </Link>
      </p>
    </form>
  );
}
