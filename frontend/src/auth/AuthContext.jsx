// AuthContext.jsx — REMEMBERS WHO IS LOGGED IN, FOR THE WHOLE APP.
//
// A "context" is a shared box of data that any page can open.
// This box holds:
//   user     → the logged-in user { id, email, full_name, role }, or null if logged out
//   loading  → true while we are still checking if someone is logged in
//   login()    → log in with email + password + role (+ "Remember me")
//   register() → create a new account (and log in)
//   logout()   → log out
//   setUser()  → update the remembered user, e.g. after a student changes their name
//
// Any page can use it like this:
//   const { user, logout } = useAuth();

import { createContext, useContext, useEffect, useState } from "react";
import { api, clearToken, getToken, saveToken } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // When the app first opens (or the page is refreshed): if we have a saved token,
  // ask the backend "who am I?" so the user stays logged in.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api("/users/me")
      .then(setUser)
      .catch(() => clearToken()) // token no longer works → forget it
      .finally(() => setLoading(false));
  }, []);

  // After login OR registration, the backend sends back { access_token, user }.
  // Save the token and remember the user.
  // remember = "Remember me" was ticked → keep the token after the browser closes.
  function startSession(data, remember = false) {
    saveToken(data.access_token, remember);
    setUser(data.user);
    return data.user;
  }

  // Send email + password + chosen role (+ "Remember me") to the backend.
  // If wrong, this throws an error with the backend's message (e.g. "Invalid email or password").
  async function login(email, password, role, remember = false) {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, role, remember_me: remember }),
    });
    return startSession(data, remember);
  }

  // Create a new account. The backend logs the new user in right away.
  // If it fails, this throws an error (e.g. "An account with this email already exists").
  // studentInfo is only for students: { enrollmentStatus, startTerm, startYear }.
  async function register(fullName, email, password, role, studentInfo = {}) {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: fullName,
        email,
        password,
        role,
        enrollment_status: studentInfo.enrollmentStatus,
        start_term: studentInfo.startTerm,
        start_year: studentInfo.startYear,
      }),
    });
    return startSession(data);
  }

  function logout() {
    clearToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

// Shortcut so pages can write useAuth() instead of useContext(AuthContext).
export function useAuth() {
  return useContext(AuthContext);
}
