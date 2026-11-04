// Toast.jsx — A SHORT SUCCESS MESSAGE IN THE CORNER OF THE SCREEN THAT DISAPPEARS BY ITSELF.
// Any page can show one with: const showToast = useToast(); showToast("Saved.");
// It's only for successes. Errors stay next to the form, so they don't disappear before they're read.

// createContext shares showToast with every page, and the others remember values and run code on the page.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

// How long a message stays on screen: 4 seconds.
const VISIBLE_MS = 4000;

// Holds the showToast function for the pages to use.
const ToastContext = createContext(null);

// One message on screen.
function ToastMessage({ message }) {
  // The message's element on the page.
  const toastRef = useRef(null);

  // Put the message on top of everything when it appears.
  useEffect(() => {
    // Get the element.
    const toast = toastRef.current;
    // An open popup covers the normal page, but a popover can sit above it. An older browser just shows it in the corner.
    if (toast.showPopover && !toast.matches(":popover-open")) toast.showPopover();
  // The empty list means this only runs once.
  }, []);

  // Draw the message.
  return <div ref={toastRef} popover="manual" role="status" className="fixed inset-auto bottom-6 right-4 m-0 max-w-[calc(100vw-2rem)] rounded-xl border border-sage/40 bg-panel px-4 py-3 text-sm font-medium text-sage shadow-2xl sm:max-w-sm">{message}</div>;
}

// Wraps the whole app, so every page can show a message.
export function ToastProvider({ children }) {
  // The message showing now. Empty when there isn't one.
  const [toast, setToast] = useState(null);
  // Shows a message, replacing any that's already showing. The id makes each one start fresh, even with the same text.
  const showToast = useCallback((message) => setToast({ id: Date.now(), message }), []);

  // Hide each message after a few seconds.
  useEffect(() => {
    // Do nothing if there's no message.
    if (!toast) return;
    // Start the timer.
    const timer = setTimeout(() => setToast(null), VISIBLE_MS);
    // A newer message restarts the timer.
    return () => clearTimeout(timer);
  // Run this for each new message.
  }, [toast]);

  // Draw the app, plus the message if there is one.
  return (
    // Share showToast with every page.
    <ToastContext.Provider value={showToast}>
      {/* The app itself. */}
      {children}
      {/* The message. */}
      {toast && <ToastMessage key={toast.id} message={toast.message} />}
    </ToastContext.Provider>
  );
}

// Gives a page the showToast function.
export function useToast() {
  // Read it from the wrapper above.
  return useContext(ToastContext);
}
