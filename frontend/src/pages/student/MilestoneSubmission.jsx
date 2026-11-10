// MilestoneSubmission.jsx — THE BUTTON AND POPUP FOR SUBMITTING A MILESTONE'S DOCUMENTS AND TRACKING ITS REVIEW.
// It sits on the comprehensive exam, dissertation proposal and dissertation defense cards.

// useEffect runs code when something changes, useRef keeps a value between draws, and useState remembers values on the page.
import { useEffect, useRef, useState } from "react";
// api talks to the backend, and getToken gives the login token needed to download a file.
import { api, getToken } from "../../api/client.js";
// Shows a short success message.
import { useToast } from "../../components/Toast.jsx";
// The presentation dates part of the popup.
import PresentationScheduling from "./PresentationScheduling.jsx";

// The largest file allowed, matching the backend: 10 MB.
const MAX_FILE_BYTES = 10 * 1024 * 1024;
// The most files in one submission, matching the backend.
const MAX_FILES = 5;
// The text shown for each status.
const STATUS_LABELS = { not_started: "Not started", in_progress: "In progress", submitted: "Submitted", under_review: "In review", revision_requested: "Revision requested", approved: "Approved", rejected: "Rejected", document_approved: "Document approved" };

// Shows a file's size in a readable way.
function formatSize(bytes) {
  // Use MB from 1 MB upward, and KB below that.
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// Shows a date and time in a readable way.
function formatDateTime(value) {
  // For example, "Nov 2, 2026, 3:30 PM".
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

// Turns a chosen file into base64 text, which is how the backend receives it.
function readAsBase64(file) {
  // Reading a file finishes later, so return a promise.
  return new Promise((resolve, reject) => {
    // The browser's file reader.
    const reader = new FileReader();
    // The result starts with a label and a comma, so keep only the part after the comma.
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    // Report a file that couldn't be read.
    reader.onerror = () => reject(new Error(`${file.name} couldn't be read. Try choosing it again.`));
    // Start reading.
    reader.readAsDataURL(file);
  });
}

// Downloads a document to the student's computer.
async function downloadDocument(document_) {
  // Ask the backend for the file, with the login token.
  const response = await fetch(`/api/milestone-documents/${document_.id}`, { headers: { Authorization: `Bearer ${getToken()}` } });
  // Stop if the backend refused.
  if (!response.ok) throw new Error(`${document_.filename} couldn't be downloaded.`);
  // Make a temporary link to the file.
  const url = URL.createObjectURL(await response.blob());
  // Create a link element.
  const link = document.createElement("a");
  // Point it at the file.
  link.href = url;
  // Save it under its own name.
  link.download = document_.filename;
  // Click it to start the download.
  link.click();
  // Remove the temporary link.
  URL.revokeObjectURL(url);
}

// The popup's content. It receives the data from the backend, and a function that stores updated data.
function SubmissionContent({ data, onUpdate }) {
  // The files chosen for this submission.
  const [files, setFiles] = useState([]);
  // An error message to show. Empty when there's no error.
  const [error, setError] = useState("");
  // True while the files are being sent, to prevent double clicks.
  const [saving, setSaving] = useState(false);
  // Shows a short success message.
  const showToast = useToast();

  // Runs when the student chooses files.
  function chooseFiles(event) {
    // Turn the browser's list into a normal list.
    const chosen = [...event.target.files];
    // Clear any old error.
    setError("");
    // Stop if too many files were chosen.
    if (chosen.length > MAX_FILES) {
      // Explain the limit.
      setError(`Choose at most ${MAX_FILES} files.`);
      // Clear the choice.
      setFiles([]);
      // Clear the file box too.
      event.target.value = "";
      // Stop here.
      return;
    }
    // Find any file over the limit.
    const tooLarge = chosen.find((file) => file.size > MAX_FILE_BYTES);
    // Stop if there is one.
    if (tooLarge) {
      // Explain the limit.
      setError(`${tooLarge.name} is larger than 10 MB.`);
      // Clear the choice.
      setFiles([]);
      // Clear the file box too.
      event.target.value = "";
      // Stop here.
      return;
    }
    // Remember the chosen files.
    setFiles(chosen);
  }

  // Runs when the form is submitted.
  async function handleSubmit(event) {
    // Stop the browser from reloading the page.
    event.preventDefault();
    // Remember the form, because it isn't available after waiting.
    const form = event.currentTarget;
    // Clear any old error.
    setError("");
    // Disable the button while this runs.
    setSaving(true);
    // Try to send the files.
    try {
      // Encode every file.
      const encoded = await Promise.all(files.map(async (file) => ({ filename: file.name, data_base64: await readAsBase64(file) })));
      // Send them, and show the updated data from the backend.
      onUpdate(await api(`/students/me/milestones/${data.milestone_id}/submission`, { method: "POST", body: JSON.stringify({ files: encoded }) }));
      // Confirm it.
      showToast("Your submission was sent for review.");
      // Clear the chosen files.
      setFiles([]);
      // Clear the file box too.
      form.reset();
    // The backend refused or couldn't be reached.
    } catch (err) {
      // Show the message.
      setError(err.message);
    // Runs whether it worked or not.
    } finally {
      // Enable the button again.
      setSaving(false);
    }
  }

  // Runs when the student clicks a file's name.
  async function handleDownload(document_) {
    // Clear any old error.
    setError("");
    // Try to download it.
    try {
      // Start the download.
      await downloadDocument(document_);
    // The download failed.
    } catch (err) {
      // Show the message.
      setError(err.message);
    }
  }

  // Draw the popup's content.
  return (
    // Stack the sections with space between them.
    <div className="space-y-6">
      {/* The current status. */}
      <section aria-label="Current status" className="rounded-xl border border-sage/25 bg-sage/5 p-4 text-sm">
        {/* The status itself. */}
        <p className="text-mist">Status: <strong className="text-white">{data.document_approved ? STATUS_LABELS.document_approved : STATUS_LABELS[data.status] ?? data.status}</strong></p>
        {/* The attempt, once a rejection has started the second one. */}
        {data.attempt_number > 1 && <p className="mt-1 text-mist">Attempt {data.attempt_number} of {data.max_attempts}</p>}
        {/* The exact approval date and time. */}
        {data.approved_at && <p className="mt-1 font-medium text-sage">Approved on {formatDateTime(data.approved_at)}</p>}
        {/* Why the student can't submit right now, if so. */}
        {data.blocked_reasons.map((reason) => <p key={reason} className="mt-1 text-amber-200">{reason}</p>)}
      </section>

      {/* The presentation dates, after the document is uploaded. */}
      <PresentationScheduling data={data} onUpdate={onUpdate} />

      {/* The upload form, only when the student can submit. */}
      {data.can_submit && (
        // The form.
        <form onSubmit={handleSubmit} aria-labelledby="submission-form-heading" className="rounded-xl border border-line p-4">
          {/* The heading changes for a resubmission. */}
          <h3 id="submission-form-heading" className="font-display font-semibold text-white">{data.attempts.length > 0 ? "Resubmit your documents" : "Submit your documents"}</h3>
          {/* The file box. */}
          <label className="mt-3 block text-sm text-mist">
            {/* The label's text, with the limits. */}
            PDF, DOCX, PPTX or PNG files, up to {MAX_FILES} files and 10 MB each
            {/* The browser's file chooser, showing only allowed types. */}
            <input type="file" required multiple accept=".pdf,.docx,.pptx,.png" onChange={chooseFiles} className="mt-2 block w-full cursor-pointer rounded-lg border border-line bg-ink px-3 py-2 text-sm text-white file:mr-3 file:rounded-md file:border-0 file:bg-sage/20 file:px-3 file:py-1 file:text-sage" />
          </label>
          {/* The chosen files with their sizes. */}
          {files.length > 0 && <ul className="mt-3 space-y-1 text-sm text-mist/80">{files.map((file) => <li key={file.name}>{file.name} ({formatSize(file.size)})</li>)}</ul>}
          {/* Any error, such as a file that's too large. */}
          {error && <p role="alert" className="mt-3 text-sm text-amber-200">{error}</p>}
          {/* Sends the files to the advisor. */}
          <button type="submit" disabled={saving || files.length === 0} className="mt-4 rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50">{saving ? "Submitting…" : "Submit for review"}</button>
        </form>
      )}

      {/* A download error, when the form isn't showing. */}
      {!data.can_submit && error && <p role="alert" className="text-sm text-amber-200">{error}</p>}

      {/* The submissions, newest first. */}
      {data.attempts.length > 0 && (
        // The submissions section.
        <section aria-labelledby="submission-attempts-heading">
          {/* The section's heading. */}
          <h3 id="submission-attempts-heading" className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">Your submissions</h3>
          {/* The list, with space between rows. */}
          <ul className="mt-3 space-y-2">
            {/* One row for each submission. */}
            {data.attempts.map((attempt) => (
              // The row's container.
              <li key={attempt.attempt} className="rounded-xl border border-line bg-ink/40 px-4 py-3 text-sm">
                {/* The attempt number and date. */}
                <p className="font-semibold text-white">Submission {attempt.attempt} <span className="font-normal text-mist/60">· {formatDateTime(attempt.submitted_at)}</span></p>
                {/* The files in this submission. */}
                <ul className="mt-2 space-y-1">
                  {/* One line for each file. */}
                  {attempt.documents.map((document_) => (
                    // The file's line.
                    <li key={document_.id}>
                      {/* Clicking the name downloads the file. */}
                      <button type="button" onClick={() => handleDownload(document_)} className="text-left text-sage underline underline-offset-4 hover:text-sage-light">{document_.filename}</button>
                      {/* The file's size. */}
                      <span className="ml-2 text-mist/60">{formatSize(document_.size_bytes)}</span>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* The status history, newest first. */}
      {data.history.length > 0 && (
        // The history section.
        <section aria-labelledby="submission-history-heading">
          {/* The section's heading. */}
          <h3 id="submission-history-heading" className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">History</h3>
          {/* The list, with space between rows. */}
          <ul className="mt-3 space-y-2 text-sm">
            {/* One line for each change. Newest first, so the position gives a stable key. */}
            {data.history.map((entry, index) => (
              // The line's container.
              <li key={data.history.length - index} className="text-mist/80">
                {/* What changed, who did it, and when. */}
                <span className="text-white">{STATUS_LABELS[entry.status] ?? entry.status}</span> by {entry.changed_by} · {formatDateTime(entry.changed_at)}
                {/* A reviewer's comment, if there is one. */}
                {entry.comment && <p className="mt-1 rounded-lg border border-line p-2 text-mist">{entry.comment}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

// The button on the dashboard card, plus the popup it opens.
// openKey is set when a notification should open the popup directly.
export default function MilestoneSubmission({ milestoneId, milestoneName, onChanged, openKey }) {
  // The data from the backend. Empty until the popup opens.
  const [data, setData] = useState(null);
  // An error message if the data couldn't load.
  const [loadError, setLoadError] = useState("");
  // True while the popup is open.
  const [open, setOpen] = useState(false);
  // Points to the popup element on the page.
  const dialogRef = useRef(null);
  // True if the student submitted while the popup was open, so the dashboard knows to refresh.
  const changed = useRef(false);

  // Open the popup when a notification points here, so the decision and any comment are visible right away.
  useEffect(() => {
    // Only when a notification was clicked.
    if (openKey) setOpen(true);
  // Run this for each new click.
  }, [openKey]);

  // Load the data each time the popup opens, so an advisor's decision shows.
  useEffect(() => {
    // Do nothing while it's closed.
    if (!open) return;
    // Lets the request be cancelled if the popup closes.
    const controller = new AbortController();
    // Clear any old data and error.
    setData(null);
    // Clear any old error.
    setLoadError("");
    // Ask the backend for this milestone's submission.
    api(`/students/me/milestones/${milestoneId}/submission`, { signal: controller.signal })
      // Save the result, unless the request was cancelled.
      .then((result) => { if (!controller.signal.aborted) setData(result); })
      // Show any error, unless the request was cancelled.
      .catch((err) => { if (!controller.signal.aborted) setLoadError(err.message); });
    // Cancel the request if the popup closes.
    return () => controller.abort();
  // Run this each time the popup opens or closes.
  }, [open, milestoneId]);

  // Show or hide the popup when "open" changes, the same way as advisor declaration.
  useEffect(() => {
    // Do nothing while it's closed.
    if (!open) return;
    // Get the popup element.
    const dialog = dialogRef.current;
    // Remember how the page scrolled before the popup opened.
    const overflow = document.body.style.overflow;
    // Show the popup on top of the page.
    dialog.showModal();
    // Stop the page behind the popup from scrolling.
    document.body.style.overflow = "hidden";
    // When it closes, hide the popup and restore the page's scrolling.
    return () => { dialog.close(); document.body.style.overflow = overflow; };
  // Run this each time "open" changes.
  }, [open]);

  // Stores updated data after a submission.
  function handleUpdate(result) {
    // Show the new data.
    setData(result);
    // Remember that the dashboard needs to refresh.
    changed.current = true;
  }

  // Closes the popup, and refreshes the dashboard if the student submitted.
  function close() {
    // Hide the popup.
    setOpen(false);
    // Only refresh if something changed.
    if (changed.current) {
      // Reset the marker for next time.
      changed.current = false;
      // Ask the dashboard to reload its milestones.
      onChanged();
    }
  }

  // Keeps the Tab key inside the popup, the same way as advisor declaration.
  function handleKeyDown(event) {
    // Ignore every other key.
    if (event.key !== "Tab") return;
    // Find the visible controls in the popup that can be used.
    const controls = [...dialogRef.current.querySelectorAll("button, input, a[href]")]
      // Keep the ones that are enabled and on screen.
      .filter((element) => !element.disabled && element.getClientRects().length > 0);
    // The first and last controls.
    const first = controls[0], last = controls[controls.length - 1];
    // Shift+Tab on the first control moves to the last one.
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    // Tab on the last control moves to the first one.
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  // Draw the button and popup.
  return <>
    {/* The button, on the right of the card. */}
    <div className="flex justify-end">
      {/* Opens the popup. */}
      <button type="button" aria-haspopup="dialog" onClick={() => setOpen(true)} className="cursor-pointer rounded-lg border border-sage/40 bg-sage/10 px-4 py-2 text-sm font-medium text-sage hover:bg-sage/20">Submission</button>
    </div>
    {/* The popup. Pressing Escape closes it through the same function as the buttons. */}
    <dialog ref={dialogRef} aria-labelledby={`submission-title-${milestoneId}`} onKeyDown={handleKeyDown} onCancel={(event) => { event.preventDefault(); close(); }} className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded-2xl border border-sage/30 bg-panel p-0 text-mist shadow-2xl backdrop:bg-black/75 backdrop:backdrop-blur-sm">
      {/* The popup's heading and close button. */}
      <header className="flex items-start justify-between gap-4 border-b border-line p-5 sm:p-6">
        {/* The title. */}
        <h2 id={`submission-title-${milestoneId}`} className="font-display text-2xl font-bold text-white">{milestoneName}</h2>
        {/* The × button. */}
        <button type="button" onClick={close} aria-label={`Close ${milestoneName}`} className="rounded-lg border border-line px-3 py-1 text-xl hover:border-sage">×</button>
      </header>
      {/* The error, a loading message, or the content. */}
      <div className="p-5 sm:p-6">
        {/* The load error. */}
        {loadError && <p role="alert" className="text-sm text-red-300">{loadError}</p>}
        {/* A loading message. */}
        {open && !data && !loadError && <p role="status" className="text-sm text-mist/70">Loading…</p>}
        {/* The content. */}
        {open && data && <SubmissionContent data={data} onUpdate={handleUpdate} />}
      </div>
      {/* The footer stays visible while the content scrolls. */}
      <footer className="sticky bottom-0 flex justify-end border-t border-line bg-panel p-5">
        {/* Closes the popup. */}
        <button type="button" onClick={close} className="rounded-lg bg-sage px-5 py-2 text-sm font-semibold text-ink hover:bg-sage-light">Close</button>
      </footer>
    </dialog>
  </>;
}
