// NotificationBell.jsx — THE BELL IN THE NAVBAR, WITH THE UNREAD COUNT AND THE LIST OF NOTIFICATIONS.
// It's in the shared navbar, so students, faculty and the director all have it.
// A notification stays unread until it's clicked, which grays it out and opens its page.

// useEffect runs code on a timer, and useState remembers values on the page.
import { useEffect, useState } from "react";
// useNavigate opens another page without reloading.
import { useNavigate } from "react-router-dom";
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
  // Opens the page a notification points to.
  const navigate = useNavigate();
  // How many haven't been clicked yet.
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

  // Runs when a notification is clicked.
  function select(notification) {
    // Close the list.
    setOpen(false);
    // Gray it out and lower the count right away.
    setNotifications((current) => current.map((item) => (item.id === notification.id ? { ...item, is_read: true } : item)));
    // Save it, unless it's already read. This reply has no content, so it uses fetch directly.
    if (!notification.is_read) {
      // A failed save isn't worth interrupting the page, so it just shows as unread on the next check.
      fetch(`/api/notifications/${notification.id}/read`, { method: "POST", headers: { Authorization: `Bearer ${getToken()}` } }).catch(() => {});
    }
    // Open its page, if it has one.
    if (notification.link) navigate(notification.link);
  }

  // Draw the bell and the list.
  return (
    // "relative" lets the list sit just under the bell.
    <div className="relative">
      {/* The bell, which also tells screen readers the unread count. */}
      <button type="button" onClick={() => setOpen((current) => !current)} aria-expanded={open} aria-label={`Notifications, ${unread} unread`} className="relative rounded-lg border border-line px-2.5 py-1 text-mist transition-colors hover:border-sage hover:text-white">
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
              // Clicked ones are grayed out. Unread ones are bright, with a soft background.
              <li key={notification.id} className={`text-sm ${notification.is_read ? "text-mist/50" : "bg-sage/10 font-medium text-white"}`}>
                {/* Clicking marks it as read and opens its page. */}
                <button type="button" onClick={() => select(notification)} className="block w-full p-3 text-left transition-colors hover:bg-sage/15">
                  {/* The message. */}
                  <span className="block">{notification.message}</span>
                  {/* When it was created. */}
                  <span className={`mt-1 block text-xs font-normal ${notification.is_read ? "text-mist/40" : "text-mist"}`}>{new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(notification.created_at))}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
