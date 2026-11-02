// NotificationBell.jsx — THE BELL IN THE NAVBAR, WITH THE UNREAD COUNT AND THE LIST OF NOTIFICATIONS.
// It's in the shared navbar, so students, faculty and the director all have it.

// useEffect runs code on a timer, and useState remembers values on the page.
import { useEffect, useState } from "react";
// getToken is needed because this request's reply has no content, so it can't use api().
import { api, getToken } from "../api/client.js";

// How often to check for new notifications: every 60 seconds.
const REFRESH_MS = 60000;

// The bell and its list.
export default function NotificationBell() {
  // The user's notifications, newest first.
  const [notifications, setNotifications] = useState([]);
  // True while the list is showing.
  const [open, setOpen] = useState(false);
  // How many haven't been read.
  const unread = notifications.filter((notification) => !notification.is_read).length;

  // Load the notifications now, then keep checking.
  useEffect(() => {
    // Asks the backend for the latest list.
    function load() {
      // A failed check isn't worth interrupting the page, so it just tries again next time.
      api("/notifications/me").then(setNotifications).catch(() => {});
    }
    // Load them right away.
    load();
    // Check again on a timer.
    const timer = setInterval(load, REFRESH_MS);
    // Stop the timer when the page closes.
    return () => clearInterval(timer);
  // The empty list means this only starts once.
  }, []);

  // Opens or closes the list, and marks everything as read when it opens.
  function toggle() {
    // Show or hide the list.
    setOpen((current) => !current);
    // Nothing to mark if it's closing or nothing is unread.
    if (open || unread === 0) return;
    // Tell the backend. This reply has no content, so it uses fetch directly.
    fetch("/api/notifications/me/read", { method: "POST", headers: { Authorization: `Bearer ${getToken()}` } })
      // Once saved, clear the unread count on the page.
      .then((response) => { if (response.ok) setTimeout(() => setNotifications((current) => current.map((notification) => ({ ...notification, is_read: true }))), 3000); })
      // A failed save isn't worth interrupting the page, so they stay unread.
      .catch(() => {});
  }

  // Draw the bell and the list.
  return (
    // "relative" lets the list sit just under the bell.
    <div className="relative">
      {/* The bell, which also tells screen readers the unread count. */}
      <button type="button" onClick={toggle} aria-expanded={open} aria-label={`Notifications, ${unread} unread`} className="relative rounded-lg border border-line px-2.5 py-1 text-mist transition-colors hover:border-sage hover:text-white">
        {/* The bell icon, as a character. */}
        <span aria-hidden="true">🔔</span>
        {/* The unread count, only when there are some. */}
        {unread > 0 && <span aria-hidden="true" className="absolute -right-1.5 -top-1.5 min-w-5 rounded-full bg-sage px-1 text-center text-xs font-semibold text-ink">{unread}</span>}
      </button>
      {/* The list, only while it's open. */}
      {open && (
        // It floats over the page, and scrolls if it's long.
        <div className="absolute right-0 z-20 mt-2 max-h-96 w-80 max-w-[calc(100vw-2rem)] overflow-y-auto rounded-xl border border-line bg-panel shadow-2xl">
          {/* A message when there are none. */}
          {notifications.length === 0 && <p className="p-4 text-sm text-mist/60">No notifications yet.</p>}
          {/* The list itself. */}
          <ul className="divide-y divide-line">
            {/* One row for each notification. */}
            {notifications.map((notification) => (
              // Unread ones are slightly highlighted.
              <li key={notification.id} className={`p-3 text-sm ${notification.is_read ? "text-mist/70" : "bg-sage/10 text-white"}`}>
                {/* The message. */}
                <p>{notification.message}</p>
                {/* When it was created. */}
                <p className="mt-1 text-xs text-mist/50">{new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(notification.created_at))}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
