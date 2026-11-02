// UserMenu.jsx — THE PICTURE AND NAME IN THE NAVBAR, WHICH OPEN A DROPDOWN WITH PROFILE, PROGRESS AND LOG OUT.

// useEffect closes the dropdown from outside clicks, useRef finds the menu on the page, and useState remembers if it's open.
import { useEffect, useRef, useState } from "react";
// NavLink goes to another page without reloading, and highlights the current one.
import { NavLink } from "react-router-dom";
// roleLabel turns a role into readable text.
import { roleLabel } from "../auth/roles.js";
// The user's picture or initials.
import Avatar from "./Avatar.jsx";

// The shared styling for every row in the dropdown.
const ITEM = "block w-full rounded-md px-3 py-2 text-left text-sm text-mist transition-colors hover:bg-sage/15 hover:text-white";

// user is the logged-in user, links are their role's pages, and onLogout logs them out.
export default function UserMenu({ user, links, onLogout }) {
  // True while the dropdown is showing.
  const [open, setOpen] = useState(false);
  // Points to the whole menu, so clicks outside it can be detected.
  const menuRef = useRef(null);
  // Only students have profile pictures and a profile page for now.
  const isStudent = user.role === "student";

  // Close the dropdown on a click outside it, or on Escape, while it's open.
  useEffect(() => {
    // Do nothing while it's closed.
    if (!open) return;
    // Runs on every click on the page.
    function handleClick(event) {
      // Close it if the click was outside the menu.
      if (!menuRef.current.contains(event.target)) setOpen(false);
    }
    // Runs on every key press.
    function handleKey(event) {
      // Close it on Escape.
      if (event.key === "Escape") setOpen(false);
    }
    // Start listening for clicks.
    document.addEventListener("mousedown", handleClick);
    // Start listening for keys.
    document.addEventListener("keydown", handleKey);
    // Stop listening once it closes.
    return () => {
      // Stop listening for clicks.
      document.removeEventListener("mousedown", handleClick);
      // Stop listening for keys.
      document.removeEventListener("keydown", handleKey);
    };
  // Run this each time the dropdown opens or closes.
  }, [open]);

  // Gives a link's styling, highlighting the page the user is on.
  function linkClass({ isActive }) {
    // Add the highlight to the shared styling.
    return `${ITEM} ${isActive ? "font-medium text-sage" : ""}`;
  }

  // Draw the button and the dropdown.
  return (
    // "relative" lets the dropdown sit just under the button.
    <div ref={menuRef} className="relative">
      {/* The picture and name, which open or close the dropdown. */}
      <button type="button" onClick={() => setOpen((current) => !current)} aria-expanded={open} aria-controls="user-menu" className="flex items-center gap-2 rounded-lg px-2 py-1 text-mist transition-colors hover:bg-sage/15 hover:text-white">
        {/* The picture or initials. Other roles have no picture to load yet. */}
        <Avatar name={user.full_name} version={user.picture_version} loadPicture={isStudent} className="h-8 w-8 text-xs" />
        {/* The name. */}
        <span>{user.full_name}</span>
        {/* A small arrow, which turns over while the dropdown is open. */}
        <span aria-hidden="true" className={`text-mist/60 transition-transform ${open ? "rotate-180" : ""}`}>⌄</span>
      </button>
      {/* The dropdown, only while it's open. */}
      {open && (
        // It floats over the page, on the right, and stays within narrow screens.
        <div id="user-menu" className="absolute right-0 z-20 mt-2 w-56 max-w-[calc(100vw-2rem)] rounded-xl border border-line bg-panel p-2 shadow-2xl">
          {/* The user's role, as a small heading. */}
          <p className="px-3 py-1.5 text-xs text-mist/50">{roleLabel(user.role)}</p>
          {/* The profile, for students. Clicking any link closes the dropdown. */}
          {isStudent && <NavLink to="/student/profile" onClick={() => setOpen(false)} className={linkClass}>Profile</NavLink>}
          {/* The pages for this role, such as My progress. */}
          {links.map((link) => <NavLink key={link.to} to={link.to} end onClick={() => setOpen(false)} className={linkClass}>{link.label}</NavLink>)}
          {/* A line above Log out. */}
          <hr className="my-2 border-line" />
          {/* Logs the user out. */}
          <button type="button" onClick={onLogout} className={ITEM}>Log out</button>
        </div>
      )}
    </div>
  );
}
