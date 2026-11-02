// Avatar.jsx — A STUDENT'S PROFILE PICTURE, OR THEIR INITIALS IF THEY HAVEN'T ADDED ONE.

// useEffect loads the picture, and useState remembers it.
import { useEffect, useState } from "react";
// getToken is needed because a picture can't be loaded with api(), which only reads text data.
import { getToken } from "../api/client.js";

// name gives the initials and description, version reloads the picture after a change, loadPicture is false for roles
// with no picture, and className sets the size.
export default function Avatar({ name, version = 0, loadPicture = true, className = "h-7 w-7 text-xs" }) {
  // A temporary link to the picture. Empty when there isn't one.
  const [url, setUrl] = useState(null);

  // Load the picture when this appears, and again whenever "version" changes.
  useEffect(() => {
    // Roles with no picture just show their initials.
    if (!loadPicture) return;
    // True once this version is out of date, so a slow reply is ignored.
    let stale = false;
    // The temporary link made below, so it can be removed later.
    let objectUrl = null;
    // Ask the backend for the picture, with the login token.
    fetch("/api/students/me/profile/picture", { headers: { Authorization: `Bearer ${getToken()}` } })
      // Only a 200 reply contains a picture. 204 means the student hasn't added one.
      .then((response) => (response.status === 200 ? response.blob() : null))
      // Show the picture, or the initials if there isn't one.
      .then((blob) => {
        // Stop if this reply is out of date.
        if (stale) return;
        // Make a temporary link if there's a picture.
        objectUrl = blob ? URL.createObjectURL(blob) : null;
        // Use it on the page.
        setUrl(objectUrl);
      })
      // If it fails, the initials stay, which is fine.
      .catch(() => {});
    // Clean up when the version changes or this is removed.
    return () => {
      // Ignore any reply still on its way.
      stale = true;
      // Free the temporary link.
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  // Run this each time "version" changes.
  }, [version, loadPicture]);

  // The first letter of the first two words of the name, e.g. "Lisa Lee" becomes "LL".
  const initials = name.trim().split(/\s+/).slice(0, 2).map((word) => word[0]?.toUpperCase()).join("");

  // Show the picture if there is one.
  if (url) return <img src={url} alt={`${name}'s profile`} className={`shrink-0 rounded-full object-cover ${className}`} />;
  // Otherwise, show the initials in a circle.
  return <span aria-hidden="true" className={`inline-flex shrink-0 items-center justify-center rounded-full bg-sage/20 font-semibold text-sage ${className}`}>{initials}</span>;
}
