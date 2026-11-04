// main.jsx — THE STARTING POINT of the whole React app.
// The browser loads index.html, and index.html loads this file.
// You will almost never need to change this file.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./auth/AuthContext.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import "./index.css"; // turns on Tailwind styles for every page

// Find the empty <div id="root"> in index.html and draw our app inside it.
createRoot(document.getElementById("root")).render(
  // StrictMode: shows extra warnings during development to help catch bugs.
  <StrictMode>
    {/* BrowserRouter: lets us have different pages for different URLs (like /student, /faculty). */}
    <BrowserRouter>
      {/* AuthProvider: makes "who is logged in" available to every page (see auth/AuthContext.jsx). */}
      <AuthProvider>
        {/* ToastProvider: lets every page show a short success message (see components/Toast.jsx). */}
        <ToastProvider>
          <App />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
