// UserMenu.jsx — THE PICTURE AND NAME IN THE NAVBAR.
// Opens a dropdown with Profile, role-specific pages, and Log out.

import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";

import { roleLabel } from "../auth/roles.js";
import Avatar from "./Avatar.jsx";


// Shared styling for every item in the dropdown.
const ITEM =
  "block w-full rounded-md px-3 py-2 text-left text-sm text-mist transition-colors hover:bg-sage/15 hover:text-white";


export default function UserMenu({
  user,
  links,
  onLogout,
}) {
  // Whether the dropdown is currently open.
  const [open, setOpen] = useState(false);

  // Reference to the complete menu so outside clicks can close it.
  const menuRef = useRef(null);

  // Students currently have profile-picture loading.
  const isStudent = user.role === "student";

  // Faculty members now also have their own profile page.
  const isFaculty = user.role === "faculty";


  // Close the dropdown when the user clicks outside it
  // or presses Escape.
  useEffect(() => {
    if (!open) {
      return;
    }

    function handleClick(event) {
      if (
        menuRef.current &&
        !menuRef.current.contains(
          event.target
        )
      ) {
        setOpen(false);
      }
    }

    function handleKey(event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleClick
    );

    document.addEventListener(
      "keydown",
      handleKey
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClick
      );

      document.removeEventListener(
        "keydown",
        handleKey
      );
    };
  }, [open]);


  // Highlight the link for the page currently being viewed.
  function linkClass({ isActive }) {
    return `${ITEM} ${
      isActive
        ? "font-medium text-sage"
        : ""
    }`;
  }


  function closeMenu() {
    setOpen(false);
  }


  return (
    <div
      ref={menuRef}
      className="relative"
    >
      {/* User name/avatar button */}
      <button
        type="button"
        onClick={() =>
          setOpen(
            (current) => !current
          )
        }
        aria-expanded={open}
        aria-controls="user-menu"
        className="flex items-center gap-2 rounded-lg px-2 py-1 text-mist transition-colors hover:bg-sage/15 hover:text-white"
      >
        {/*
          Students currently load their saved profile picture.
          Faculty members use initials until faculty-picture
          support is added.
        */}
        <Avatar
          name={user.full_name}
          version={
            user.picture_version
          }
          loadPicture={isStudent}
          className="h-8 w-8 text-xs"
        />

        <span>
          {user.full_name}
        </span>

        <span
          aria-hidden="true"
          className={`text-mist/60 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        >
          ⌄
        </span>
      </button>


      {/* Dropdown menu */}
      {open && (
        <div
          id="user-menu"
          className="absolute right-0 z-20 mt-2 w-56 max-w-[calc(100vw-2rem)] rounded-xl border border-line bg-panel p-2 shadow-2xl"
        >
          {/* User role */}
          <p className="px-3 py-1.5 text-xs text-mist/50">
            {roleLabel(user.role)}
          </p>


          {/* Student profile */}
          {isStudent && (
            <NavLink
              to="/student/profile"
              onClick={closeMenu}
              className={linkClass}
            >
              Profile
            </NavLink>
          )}


          {/* Faculty profile */}
          {isFaculty && (
            <NavLink
              to="/faculty/profile"
              onClick={closeMenu}
              className={linkClass}
            >
              Profile
            </NavLink>
          )}


          {/* Other pages available for the user's role */}
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end
              onClick={closeMenu}
              className={linkClass}
            >
              {link.label}
            </NavLink>
          ))}


          <hr className="my-2 border-line" />


          {/* Log out */}
          <button
            type="button"
            onClick={onLogout}
            className={ITEM}
          >
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
