// App.jsx — THE MAP OF ALL PAGES.
// Each <Route> says: "when the URL is X, show page Y".
// To add a new page: create the page file, import it here, and add a <Route>
// inside the matching role's ProtectedRoute block.

import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import AuthShell from "./components/AuthShell.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import StudentDashboard from "./pages/student/StudentDashboard.jsx";
import FacultyDashboard from "./pages/faculty/FacultyDashboard.jsx";
import DirectorDashboard from "./pages/director/DirectorDashboard.jsx";

export default function App() {
  return (
    <Routes>
      {/* Login and Register pages — open to everyone, NO navbar.
          They sit inside AuthShell: the lamp screen. Turn the lamp on to see the form. */}
      <Route element={<AuthShell />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Everything below needs the user to be logged in... */}
      <Route element={<ProtectedRoute />}>
        {/* ...and gets the navbar from Layout. */}
        <Route element={<Layout />}>
          {/* Student-only pages */}
          <Route element={<ProtectedRoute role="student" />}>
            <Route path="/student" element={<StudentDashboard />} />
          </Route>

          {/* Faculty-only pages */}
          <Route element={<ProtectedRoute role="faculty" />}>
            <Route path="/faculty" element={<FacultyDashboard />} />
          </Route>

          {/* Program-director-only pages */}
          <Route element={<ProtectedRoute role="program_director" />}>
            <Route path="/program_director" element={<DirectorDashboard />} />
          </Route>
        </Route>
      </Route>

      {/* Any unknown URL → send the user to the login page. */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
