// Committee.jsx — THE BUTTON AND POPUP FOR INVITING COMMITTEE MEMBERS AND TRACKING RESPONSES.
// It sits on the dashboard's Committee formation card. The requirement check comes from the backend, so the rules live in one place.

// useEffect runs code when something changes, useRef keeps a value between draws, and useState remembers values on the page.
import { useEffect, useRef, useState } from "react";
// api is the one function that talks to the backend.
import { api } from "../../api/client.js";
// The app's own "are you sure?" box.
import ConfirmDialog from "../../components/ConfirmDialog.jsx";

// The same styling for every dropdown and input on the form.
const FIELD = "mt-1 w-full rounded-lg border border-line bg-ink px-3 py-2 text-sm text-white focus:border-sage focus:outline-none";
// The text shown for each status.
const STATUS_LABELS = { pending: "Pending", approved: "Approved", declined: "Declined" };

// Returns an empty invitation form.
function emptyForm() {
  // No faculty member is selected, and the external fields are empty.
  return { is_external: false, faculty_id: "", external_name: "", external_affiliation: "" };
}

// The popup's content. It receives the data from the backend, and a function that stores updated data.
function CommitteeContent({ data, onUpdate }) {
  // The current values in the form.
  const [form, setForm] = useState(emptyForm());
  // An error message to show. Empty when there's no error.
  const [error, setError] = useState("");
  // True while a request is being saved, to prevent double clicks.
  const [saving, setSaving] = useState(false);
  // The person waiting to be confirmed for removal. Empty when the box isn't showing.
  const [memberToRemove, setMemberToRemove] = useState(null);

  // Updates one field in the form.
  function setField(name, value) {
    // Keep the other fields and replace this one.
    setForm((current) => ({ ...current, [name]: value }));
  }

  // Sends a request and shows the updated data.
  async function send(path, options) {
    // Clear any old error.
    setError("");
    // Disable the buttons while this runs.
    setSaving(true);
    // Try the request.
    try {
      // Show the updated committee from the backend.
      onUpdate(await api(path, options));
      // Report success to the caller.
      return true;
    // The backend refused the request or couldn't be reached.
    } catch (err) {
      // Show its message.
      setError(err.message);
      // Report failure to the caller.
      return false;
    // Runs whether it worked or not.
    } finally {
      // Enable the buttons again.
      setSaving(false);
    }
  }

  // Runs when the form is submitted.
  async function handleSubmit(event) {
    // Stop the browser from reloading the page.
    event.preventDefault();
    // Send the external member's details, or the faculty member's id.
    const body = form.is_external
      // The external member's details.
      ? { external_name: form.external_name, external_affiliation: form.external_affiliation }
      // The faculty member's id.
      : { faculty_id: Number(form.faculty_id) };
    // Send the request.
    const saved = await send("/students/me/committee", { method: "POST", body: JSON.stringify(body) });
    // Clear the form only if it saved.
    if (saved) setForm(emptyForm());
  }

  // Runs when the student confirms the removal in the box.
  async function confirmRemove() {
    // Remember who is being removed.
    const member = memberToRemove;
    // Close the box.
    setMemberToRemove(null);
    // Delete the row.
    await send(`/students/me/committee/${member.id}`, { method: "DELETE" });
  }

  // Draw the popup's content.
  return (
    // Stack the sections with space between them.
    <div className="space-y-6">
      {/* The requirement check. */}
      <section aria-label="Committee requirements" className="rounded-xl border border-sage/25 bg-sage/5 p-4 text-sm text-mist">
        {/* The members requirement. */}
        <p>At least {data.required_members} approved members: <strong className={data.approved_count >= data.required_members ? "text-sage" : "text-white"}>{data.approved_count} of {data.required_members}</strong></p>
        {/* The CS requirement. */}
        <p className="mt-1">At least {data.required_cs} from the CS department: <strong className={data.cs_count >= data.required_cs ? "text-sage" : "text-white"}>{data.cs_count} of {data.required_cs}</strong></p>
        {/* Confirm when both are met. */}
        {data.complete && <p className="mt-2 font-medium text-sage">Your committee requirement is complete.</p>}
      </section>

      {/* The list of people. */}
      <section aria-labelledby="committee-members-heading">
        {/* The section's heading. */}
        <h3 id="committee-members-heading" className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">Committee members</h3>
        {/* A message if there's no advisor, so no chair yet. */}
        {data.members.length === 0 && <p className="mt-3 rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">Your research advisor will appear here as your committee chair.</p>}
        {/* The list, with space between rows. */}
        <ul className="mt-3 space-y-2">
          {/* One row for each person. */}
          {data.members.map((member) => (
            // The row's container. The advisor has no id, so they use a fixed key.
            <li key={member.id ?? "chair"} className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-ink/40 px-4 py-3 text-sm">
              {/* The person's name and details, taking up the free space. */}
              <div className="min-w-0 flex-1 basis-48">
                {/* The name, marked if they're the chair. */}
                <p className="font-semibold text-white">{member.name}{member.is_chair ? " (chair, your advisor)" : ""}</p>
                {/* Their department or affiliation, and whether they're external. */}
                <p className="text-mist/70">{member.detail ?? "Department not recorded"}{member.is_external ? " · External member" : ""}</p>
              </div>
              {/* The response. */}
              <span className={`rounded-full border px-3 py-1 text-xs ${member.status === "approved" ? "border-sage/25 bg-sage/10 text-sage" : member.status === "declined" ? "border-amber-300/30 text-amber-200" : "border-line text-mist"}`}>{STATUS_LABELS[member.status] ?? member.status}</span>
              {/* Remove shows for everyone except the chair. */}
              {member.can_remove && <button type="button" disabled={saving} onClick={() => setMemberToRemove(member)} className="text-mist/70 underline underline-offset-4 hover:text-white disabled:opacity-50">Remove</button>}
            </li>
          ))}
        </ul>
      </section>

      {/* The invitation form, or a message if the advisor must come first. */}
      {!data.advisor_declared ? <p className="rounded-xl border border-line p-4 text-sm text-amber-200">Declare your research advisor first. They chair your committee.</p> : (
        // The form.
        <form onSubmit={handleSubmit} aria-labelledby="committee-form-heading" className="rounded-xl border border-line p-4">
          {/* The form's heading. */}
          <h3 id="committee-form-heading" className="font-display font-semibold text-white">Invite a member</h3>
          {/* The switch to external entry. */}
          <label className="mt-3 flex items-center gap-2 text-sm text-mist">
            {/* Ticking this replaces the faculty dropdown with the external fields. */}
            <input type="checkbox" checked={form.is_external} onChange={(event) => setForm({ ...emptyForm(), is_external: event.target.checked })} />
            {/* The checkbox's text. */}
            This person is an external member with no GradTrack account
          </label>
          {/* The faculty dropdown, unless the person is external. */}
          {!form.is_external && (
            // The field's label.
            <label className="mt-3 block text-sm text-mist">
              {/* The label's text. */}
              Faculty member
              {/* The dropdown itself. */}
              <select required value={form.faculty_id} onChange={(event) => setField("faculty_id", event.target.value)} className={FIELD}>
                {/* The first option, shown before anything is picked. */}
                <option value="">Select a faculty member</option>
                {/* One option for each faculty member who can still be invited. */}
                {data.faculty_options.map((person) => <option key={person.id} value={person.id}>{person.full_name}{person.department ? ` — ${person.department}` : ""}</option>)}
              </select>
            </label>
          )}
          {/* The external member's name. */}
          {form.is_external && (
            // The field's label.
            <label className="mt-3 block text-sm text-mist">
              {/* The label's text. */}
              Name
              {/* The person's name. */}
              <input type="text" required maxLength={255} value={form.external_name} onChange={(event) => setField("external_name", event.target.value)} className={FIELD} />
            </label>
          )}
          {/* The external member's affiliation. */}
          {form.is_external && (
            // The field's label.
            <label className="mt-3 block text-sm text-mist">
              {/* The label's text. */}
              University or company
              {/* Where the person works. */}
              <input type="text" required maxLength={255} value={form.external_affiliation} onChange={(event) => setField("external_affiliation", event.target.value)} className={FIELD} />
            </label>
          )}
          {/* Explain that an external member is approved right away. */}
          {form.is_external && <p className="mt-2 text-xs text-mist/60">External members have no account, so they're approved as soon as you add them. They don't count toward the CS members.</p>}
          {/* Any error, such as inviting someone twice. */}
          {error && <p role="alert" className="mt-3 text-sm text-amber-200">{error}</p>}
          {/* Sends the invitation. */}
          <button type="submit" disabled={saving} className="mt-4 rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:opacity-50">{saving ? "Saving…" : form.is_external ? "Add member" : "Send invitation"}</button>
        </form>
      )}
      {/* The "are you sure?" box, while a removal is waiting to be confirmed. A complete committee also gets a warning. */}
      {memberToRemove && <ConfirmDialog title={`Remove ${memberToRemove.name}?`} message={data.complete ? "If your committee no longer meets the requirements, Committee formation goes back to In progress." : undefined} confirmLabel="Remove" onConfirm={confirmRemove} onCancel={() => setMemberToRemove(null)} />}
    </div>
  );
}

// The summary and button on the dashboard card, plus the popup they open.
export default function Committee({ onChanged }) {
  // The data from the backend. Empty until it loads.
  const [data, setData] = useState(null);
  // An error message if the data couldn't load.
  const [loadError, setLoadError] = useState("");
  // True while the popup is open.
  const [open, setOpen] = useState(false);
  // Points to the popup element on the page.
  const dialogRef = useRef(null);

  // Load the data when the card appears and each time the popup opens, so new responses show.
  useEffect(() => {
    // Lets the request be cancelled if the dashboard closes.
    const controller = new AbortController();
    // Ask the backend for the committee.
    api("/students/me/committee", { signal: controller.signal })
      // Save the result, unless the request was cancelled.
      .then((result) => { if (!controller.signal.aborted) setData(result); })
      // Show any error, unless the request was cancelled.
      .catch((err) => { if (!controller.signal.aborted) setLoadError(err.message); });
    // Cancel the request if the dashboard closes.
    return () => controller.abort();
  // Run this each time "open" changes.
  }, [open]);

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

  // Closes the popup, and refreshes the dashboard because a response may have changed its status.
  function close() {
    // Hide the popup.
    setOpen(false);
    // Ask the dashboard to reload its milestones.
    onChanged();
  }

  // Keeps the Tab key inside the popup, the same way as advisor declaration.
  function handleKeyDown(event) {
    // Ignore every other key.
    if (event.key !== "Tab") return;
    // Find the visible controls in the popup that can be used.
    const controls = [...dialogRef.current.querySelectorAll("button, input, select, a[href]")]
      // Keep the ones that are enabled and on screen.
      .filter((element) => !element.disabled && element.getClientRects().length > 0);
    // The first and last controls.
    const first = controls[0], last = controls[controls.length - 1];
    // Shift+Tab on the first control moves to the last one.
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    // Tab on the last control moves to the first one.
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  // Draw the summary, button and popup.
  return <>
    {/* The summary on the left, and the button on the right. */}
    <div className="flex flex-wrap items-center justify-between gap-4">
      {/* The load error, the summary, or a loading message. */}
      <p className={loadError ? "text-red-300" : "text-mist"}>{loadError || (data ? `${data.approved_count} of ${data.required_members} members approved, ${data.cs_count} of ${data.required_cs} from CS` : "Loading your committee…")}</p>
      {/* Opens the popup, once the data has loaded. */}
      <button type="button" aria-haspopup="dialog" disabled={!data} onClick={() => setOpen(true)} className="cursor-pointer rounded-lg border border-sage/40 bg-sage/10 px-4 py-2 text-sm font-medium text-sage hover:bg-sage/20 disabled:cursor-not-allowed disabled:opacity-50">Manage committee</button>
    </div>
    {/* The popup. Pressing Escape closes it through the same function as the buttons. */}
    <dialog ref={dialogRef} aria-labelledby="committee-title" onKeyDown={handleKeyDown} onCancel={(event) => { event.preventDefault(); close(); }} className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-2xl border border-sage/30 bg-panel p-0 text-mist shadow-2xl backdrop:bg-black/75 backdrop:backdrop-blur-sm">
      {/* The popup's heading and close button. */}
      <header className="flex items-start justify-between gap-4 border-b border-line p-5 sm:p-6">
        {/* The title and explanation. */}
        <div>
          {/* The popup's title. */}
          <h2 id="committee-title" className="font-display text-2xl font-bold text-white">Committee</h2>
          {/* A short explanation. */}
          <p className="mt-2 text-sm text-mist/70">Invite faculty members and track their responses. Your research advisor is your committee chair.</p>
        </div>
        {/* The × button. */}
        <button type="button" onClick={close} aria-label="Close committee" className="rounded-lg border border-line px-3 py-1 text-xl hover:border-sage">×</button>
      </header>
      {/* The content, which is rebuilt each time so the form starts empty. */}
      <div className="p-5 sm:p-6">{open && data && <CommitteeContent data={data} onUpdate={setData} />}</div>
      {/* The footer stays visible while the content scrolls. */}
      <footer className="sticky bottom-0 flex justify-end border-t border-line bg-panel p-5">
        {/* Closes the popup. */}
        <button type="button" onClick={close} className="rounded-lg bg-sage px-5 py-2 text-sm font-semibold text-ink hover:bg-sage-light">Close</button>
      </footer>
    </dialog>
  </>;
}
