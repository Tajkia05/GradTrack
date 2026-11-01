// ConfirmDialog.jsx — THE APP'S OWN "ARE YOU SURE?" BOX, USED INSTEAD OF THE BROWSER'S POPUP.
// Show it only while a question is waiting for an answer. It can open on top of another popup.

// useEffect runs code when the box appears, and useRef points to the box on the page.
import { useEffect, useRef } from "react";

// title is the question, message adds detail, confirmLabel names the action, and the two functions handle the answer.
export default function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel }) {
  // Points to the box on the page.
  const dialogRef = useRef(null);

  // Show the box when it appears on the page.
  useEffect(() => {
    // Get the box.
    const dialog = dialogRef.current;
    // Show it on top of everything, including another popup.
    dialog.showModal();
    // Hide it when it's removed from the page.
    return () => dialog.close();
  // The empty list means this only runs once.
  }, []);

  // Keeps key presses inside this box, so they don't also reach a popup behind it.
  function handleKeyDown(event) {
    // Stop the key press from reaching the popup behind.
    event.stopPropagation();
    // Ignore every key except Tab.
    if (event.key !== "Tab") return;
    // Find the two buttons.
    const buttons = [...dialogRef.current.querySelectorAll("button")];
    // The first and last buttons.
    const first = buttons[0], last = buttons[buttons.length - 1];
    // Shift+Tab on the first button moves to the last one.
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    // Tab on the last button moves to the first one.
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  // Draw the box.
  return (
    // Escape counts as Cancel, and only closes this box, not a popup behind it.
    <dialog ref={dialogRef} role="alertdialog" aria-labelledby="confirm-title" aria-describedby={message ? "confirm-message" : undefined} onKeyDown={handleKeyDown} onCancel={(event) => { event.preventDefault(); event.stopPropagation(); onCancel(); }} className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-sage/30 bg-panel p-6 text-mist shadow-2xl backdrop:bg-black/75 backdrop:backdrop-blur-sm">
      {/* The question. */}
      <h2 id="confirm-title" className="font-display text-lg font-semibold text-white">{title}</h2>
      {/* The extra detail, if there is any. */}
      {message && <p id="confirm-message" className="mt-2 text-sm leading-relaxed text-mist/80">{message}</p>}
      {/* The two buttons, on the right. */}
      <div className="mt-6 flex justify-end gap-3">
        {/* Keeps things as they are. It starts selected, so pressing Enter by accident changes nothing. */}
        <button type="button" autoFocus onClick={onCancel} className="rounded-lg border border-line px-4 py-2 text-sm text-mist hover:border-sage hover:text-white">Cancel</button>
        {/* Carries out the action. */}
        <button type="button" onClick={onConfirm} className="rounded-lg bg-amber-200 px-4 py-2 text-sm font-semibold text-ink hover:bg-amber-100">{confirmLabel}</button>
      </div>
    </dialog>
  );
}
