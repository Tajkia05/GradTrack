// AuthShell.jsx — THE "LAMP" SCREEN AROUND THE LOGIN AND REGISTER PAGES.
//
//   ┌──────────────── LEFT ────────────────┬──────────────── RIGHT ───────────────┐
//   │ GradTrack                            │                                      │
//   │               💡 lamp                │   lamp OFF: dark and empty           │
//   │          (in the middle)             │   lamp ON:  green glow + the form    │
//   │       Click the lamp to sign in      │                                      │
//   └──────────────────────────────────────┴──────────────────────────────────────┘
//
// It works like Layout.jsx: in App.jsx, Login and Register are placed INSIDE it,
// and <Outlet /> shows whichever one matches the URL (/login or /register).
// Because this frame stays on screen when you switch between them, the lamp stays on.

import { useState } from "react";
import { Outlet } from "react-router-dom";
import Lamp from "./Lamp.jsx";
import logo from "../assets/gradtrack-logo.png";

// Remember "the lamp is on" for this browser tab, so a refresh doesn't switch it off.
// (Wrapped in try/catch because some browsers block storage — then we just forget.)
const LAMP_KEY = "gradtrack_lamp_on";
function readLamp() {
  try { return sessionStorage.getItem(LAMP_KEY) === "1"; } catch { return false; }
}
function saveLamp(on) {
  try { sessionStorage.setItem(LAMP_KEY, on ? "1" : "0"); } catch { /* ignore */ }
}

export default function AuthShell() {
  const [lampOn, setLampOn] = useState(readLamp);

  function toggleLamp() {
    const next = !lampOn;
    setLampOn(next);
    saveLamp(next);
  }

  return (
    // "is-lit" switches on all the light effects in index.css.
    <div className={"flex min-h-screen flex-col bg-ink text-mist md:flex-row " + (lampOn ? "is-lit" : "")}>
      {/* ---------- LEFT: GradTrack name + the lamp in the middle ---------- */}
      <section className="lamp-room relative flex flex-col items-center justify-center gap-6 px-6 pb-8 pt-10 md:w-1/2 md:p-12">
        <div className="text-center md:absolute md:left-12 md:top-10 md:text-left">
          {/* The GradTrack logo (graduation cap + name). */}
          <img src={logo} alt="GradTrack" className="mx-auto h-auto w-32 md:mx-0 md:w-40" />
          <p className="mt-2 text-sm text-mist/60">Graduate degree progress, in one place</p>
        </div>

        <Lamp on={lampOn} onToggle={toggleLamp} />

        {/* Hint under the lamp. */}
        <p className="text-sm text-mist/60 md:absolute md:bottom-10">
          {lampOn ? "Click the lamp to switch it off" : "Click the lamp to sign in"}
        </p>
      </section>

      {/* ---------- RIGHT: dark until the lamp is on, then the form appears ---------- */}
      <section className="lamp-stage relative flex flex-1 items-center justify-center px-4 py-10 md:w-1/2">
        {/* Glowing line between the two halves + soft green glow (styles in index.css). */}
        <div className="lamp-edge" aria-hidden="true" />
        <div className="lamp-light" aria-hidden="true" />

        {lampOn ? (
          <div className="lamp-reveal relative w-full max-w-sm">
            <Outlet />
          </div>
        ) : (
          // Screen readers get a hint; sighted users just see the dark side.
          <p className="sr-only">Turn on the lamp to show the sign-in form.</p>
        )}
      </section>
    </div>
  );
}
