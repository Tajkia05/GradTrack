// Register.jsx — THE SIGN-UP PAGE. URL: /register
// Who uses it: new users who don't have an account yet.
//
// The user picks their role, fills in name, email and password, and we ask the backend
// to create the account. The backend logs them in right away, so we send them
// straight to their own dashboard.

import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import RoleSelector from "../components/RoleSelector.jsx";

const MIN_PASSWORD_LENGTH = 8; // must match the backend rule in users/schemas.py

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();

  // One memory box per form field, plus the error message and "waiting" flag.
  const [role, setRole] = useState("student");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Already logged in? No need to register — go to your dashboard.
  if (user) return <Navigate to={`/${user.role}`} replace />;

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    // Quick checks in the browser first, so the user gets instant feedback.
    // (The backend checks again — never trust only the browser.)
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (password !== confirmPassword) {
      setError("The two passwords don't match.");
      return;
    }

    setSubmitting(true);
    try {
      const newUser = await register(fullName, email, password, role);
      navigate(`/${newUser.role}`, { replace: true });
    } catch (err) {
      setError(err.message); // e.g. "An account with this email already exists..."
    } finally {
      setSubmitting(false);
    }
  }

  return (
    // The lamp screen around this card comes from components/AuthShell.jsx.
    <form onSubmit={handleSubmit} className="auth-card w-full rounded-2xl p-6">
      <h1 className="mb-5 font-display text-2xl font-bold text-white">Create your account</h1>

      {/* The three role buttons. */}
      <RoleSelector value={role} onChange={setRole} />

      <label className="mb-1 block text-sm font-medium text-mist" htmlFor="fullName">Full name</label>
      <input
        id="fullName"
        type="text"
        required
        autoComplete="name"
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        className="mb-3 w-full rounded-lg border border-line bg-ink px-3 py-2 text-white outline-none transition focus:border-sage focus:ring-2 focus:ring-sage/30"
      />

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
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full rounded-lg border border-line bg-ink px-3 py-2 text-white outline-none transition focus:border-sage focus:ring-2 focus:ring-sage/30"
      />
      <p className="mb-3 mt-1 text-xs text-mist/50">At least {MIN_PASSWORD_LENGTH} characters.</p>

      <label className="mb-1 block text-sm font-medium text-mist" htmlFor="confirmPassword">Confirm password</label>
      <input
        id="confirmPassword"
        type="password"
        required
        autoComplete="new-password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        className="mb-3 w-full rounded-lg border border-line bg-ink px-3 py-2 text-white outline-none transition focus:border-sage focus:ring-2 focus:ring-sage/30"
      />

      {/* Only shown when something went wrong. */}
      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-sage py-2 font-semibold text-ink transition hover:bg-sage-light disabled:opacity-50"
      >
        {submitting ? "Creating account..." : "Create account"}
      </button>

      {/* Link back to the login page. */}
      <p className="mt-4 text-center text-sm text-mist/70">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-sage hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
