// App.jsx — THE MAP OF ALL PAGES.
// Each <Route> says which page should appear for a URL.
// Role-specific pages stay inside their matching ProtectedRoute.

import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute.jsx";
import AuthShell from "./components/AuthShell.jsx";
import Layout from "./components/Layout.jsx";

import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";

import StudentDashboard from "./pages/student/StudentDashboard.jsx";
import StudentProfile from "./pages/student/StudentProfile.jsx";

import FacultyDashboard from "./pages/faculty/FacultyDashboard.jsx";
import FacultyProfile from "./pages/faculty/FacultyProfile.jsx";
import StudentProgress from "./pages/faculty/StudentProgress.jsx";

import DirectorDashboard from "./pages/director/DirectorDashboard.jsx";


export default function App() {
  return (
    <Routes>
      {/*
        Login and Register are public pages.
        They use AuthShell and do not show the main navbar.
      */}
      <Route element={<AuthShell />}>
        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/register"
          element={<Register />}
        />
      </Route>


      {/* Everything below requires authentication. */}
      <Route element={<ProtectedRoute />}>
        {/* Logged-in pages use the shared navbar/layout. */}
        <Route element={<Layout />}>


          {/* Student-only pages */}
          <Route
            element={
              <ProtectedRoute role="student" />
            }
          >
            <Route
              path="/student"
              element={<StudentDashboard />}
            />

            <Route
              path="/student/profile"
              element={<StudentProfile />}
            />
          </Route>


          {/* Faculty-only pages */}
          <Route
            element={
              <ProtectedRoute role="faculty" />
            }
          >
            {/* Faculty dashboard */}
            <Route
              path="/faculty"
              element={<FacultyDashboard />}
            />

            {/* Faculty member's own profile */}
            <Route
              path="/faculty/profile"
              element={<FacultyProfile />}
            />

            {/*
              Detailed progress for one of the
              faculty member's assigned students.
            */}
            <Route
              path="/faculty/students/:studentId/progress"
              element={<StudentProgress />}
            />
          </Route>


          {/* Program-director-only pages */}
          <Route
            element={
              <ProtectedRoute role="program_director" />
            }
          >
            <Route
              path="/program_director"
              element={<DirectorDashboard />}
            />
          </Route>


        </Route>
      </Route>


      {/* Unknown URLs return to login. */}
      <Route
        path="*"
        element={
          <Navigate
            to="/login"
            replace
          />
        }
      />
    </Routes>
  );
}
