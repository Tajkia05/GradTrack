// StudentProfile.jsx — THE PAGE WHERE A STUDENT VIEWS AND EDITS THEIR OWN PROFILE. URL: /student/profile
// Students reach it by clicking their name in the navbar.

// useEffect loads the profile when the page opens, and useState remembers values on the page.
import { useEffect, useState } from "react";
// Link goes back to the dashboard without reloading the page.
import { Link } from "react-router-dom";
// api is the one function that talks to the backend.
import { api } from "../../api/client.js";
// useAuth updates the name shown in the navbar.
import { useAuth } from "../../auth/AuthContext.jsx";
// The student's picture or initials.
import Avatar from "../../components/Avatar.jsx";
// The app's own "are you sure?" box.
import ConfirmDialog from "../../components/ConfirmDialog.jsx";
// Shows a short success message.
import { useToast } from "../../components/Toast.jsx";

// The same styling for every input on the form.
const FIELD = "mt-1 w-full rounded-lg border border-line bg-ink px-3 py-2 text-sm text-white focus:border-sage focus:outline-none";
// The largest picture allowed, matching the backend: 2 MB.
const MAX_PICTURE_BYTES = 2 * 1024 * 1024;

// The optional fields a student can edit.
const EDITABLE_FIELDS = ["research_interests", "lab_name", "education", "bio", "portfolio_url", "github_url", "scholar_url", "linkedin_url"];
// The four link fields, with their labels and example addresses.
const LINK_FIELDS = [
  { name: "portfolio_url", label: "Personal website", placeholder: "https://" }, // Their own site.
  { name: "github_url", label: "GitHub", placeholder: "https://github.com/your-username" }, // Their code.
  { name: "scholar_url", label: "Google Scholar", placeholder: "https://scholar.google.com/citations?user=..." }, // Their publications.
  { name: "linkedin_url", label: "LinkedIn", placeholder: "https://www.linkedin.com/in/your-name" }, // Their career profile.
];

// Turns a chosen picture into base64 text, which is how the backend receives it.
function readAsBase64(file) {
  // Reading a file finishes later, so return a promise.
  return new Promise((resolve, reject) => {
    // The browser's file reader.
    const reader = new FileReader();
    // The result starts with a label and a comma, so keep only the part after the comma.
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    // Report a file that couldn't be read.
    reader.onerror = () => reject(new Error("This picture couldn't be read. Try choosing it again."));
    // Start reading.
    reader.readAsDataURL(file);
  });
}

// One labeled piece of information in view mode.
function Detail({ label, children }) {
  // Draw the label and the value.
  return (
    // One row in the details list.
    <div className="border-t border-line py-4 first:border-t-0 first:pt-0 last:pb-0">
      {/* The label. */}
      <dt className="text-xs font-medium uppercase tracking-wider text-sage">{label}</dt>
      {/* The value, or a note if it's empty. whitespace-pre-line keeps the student's line breaks. */}
      <dd className="mt-1 whitespace-pre-line break-words text-mist">{children || <span className="text-mist/50">Not added yet</span>}</dd>
    </div>
  );
}

// The profile page.
export default function StudentProfile() {
  // The saved profile. Empty until it loads.
  const [profile, setProfile] = useState(null);
  // The values in the form. Empty while viewing, and filled while editing.
  const [form, setForm] = useState(null);
  // An error message to show. Empty when there's no error.
  const [error, setError] = useState("");
  // True while saving, to prevent double clicks.
  const [saving, setSaving] = useState(false);
  // Shows a short success message.
  const showToast = useToast();
  // True while the picture is uploading or being removed.
  const [pictureBusy, setPictureBusy] = useState(false);
  // True while the "remove picture?" box is showing.
  const [confirmingRemove, setConfirmingRemove] = useState(false);
  // Updates the name and picture shown in the navbar.
  const { user, setUser } = useAuth();

  // Load the profile once, when the page opens.
  useEffect(() => {
    // Lets the request be cancelled if the student leaves the page.
    const controller = new AbortController();
    // Ask the backend for the profile.
    api("/students/me/profile", { signal: controller.signal })
      // Save the result, unless the request was cancelled.
      .then((result) => { if (!controller.signal.aborted) setProfile(result); })
      // Show any error, unless the request was cancelled.
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    // Cancel the request if the page closes.
    return () => controller.abort();
  // The empty list means this only runs once.
  }, []);

  // Updates one field in the form.
  function setField(name, value) {
    // Keep the other fields and replace this one.
    setForm((current) => ({ ...current, [name]: value }));
  }

  // Runs when the student clicks Edit profile.
  function startEditing() {
    // Clear any old error.
    setError("");
    // Copy the saved values into the form, turning empty fields into blank text.
    setForm({ full_name: profile.full_name, ...Object.fromEntries(EDITABLE_FIELDS.map((field) => [field, profile[field] ?? ""])) });
  }

  // Runs when the student clicks Cancel.
  function cancelEditing() {
    // Clear any error from the form.
    setError("");
    // Go back to viewing, without saving.
    setForm(null);
  }

  // Runs when the form is submitted.
  async function handleSubmit(event) {
    // Stop the browser from reloading the page.
    event.preventDefault();
    // Clear any old error.
    setError("");
    // Disable the buttons while this runs.
    setSaving(true);
    // Try to save.
    try {
      // Send the form to the backend.
      const result = await api("/students/me/profile", { method: "PUT", body: JSON.stringify(form) });
      // Show the saved values.
      setProfile(result);
      // Show the new name in the navbar.
      setUser((current) => ({ ...current, full_name: result.full_name }));
      // Go back to viewing.
      setForm(null);
      // Confirm it.
      showToast("Your profile has been saved.");
    // The backend refused or couldn't be reached.
    } catch (err) {
      // Show the message.
      setError(err.message);
    // Runs whether it worked or not.
    } finally {
      // Enable the buttons again.
      setSaving(false);
    }
  }

  // Sends a picture change to the backend, then reloads the picture everywhere it's shown.
  async function changePicture(options, successMessage) {
    // Clear any old error.
    setError("");
    // Disable the picture buttons while this runs.
    setPictureBusy(true);
    // Try the request.
    try {
      // Save the change, and keep the updated profile.
      setProfile(await api("/students/me/profile/picture", options));
      // Changing this number reloads the picture in the navbar and on this page.
      setUser((current) => ({ ...current, picture_version: (current.picture_version ?? 0) + 1 }));
      // Confirm it.
      showToast(successMessage);
    // The backend refused or couldn't be reached.
    } catch (err) {
      // Show the message.
      setError(err.message);
    // Runs whether it worked or not.
    } finally {
      // Enable the picture buttons again.
      setPictureBusy(false);
    }
  }

  // Runs when the student chooses a picture.
  async function choosePicture(event) {
    // Get the chosen file.
    const file = event.target.files[0];
    // Clear the file box, so the same picture can be chosen again later.
    event.target.value = "";
    // Stop if nothing was chosen.
    if (!file) return;
    // Stop if it's too large, before sending anything.
    if (file.size > MAX_PICTURE_BYTES) {
      // Explain the limit.
      setError("The picture must be 2 MB or smaller.");
      // Stop here.
      return;
    }
    // Try to read and send it.
    try {
      // Encode it, then upload it.
      await changePicture({ method: "PUT", body: JSON.stringify({ data_base64: await readAsBase64(file) }) }, "Your profile picture has been updated.");
    // The file couldn't be read.
    } catch (err) {
      // Show the message.
      setError(err.message);
    }
  }

  // Runs when the student confirms removing their picture.
  async function confirmRemovePicture() {
    // Close the box.
    setConfirmingRemove(false);
    // Remove the picture.
    await changePicture({ method: "DELETE" }, "Your profile picture has been removed.");
  }

  // Show the error if the profile couldn't load.
  if (!profile && error) return <p role="alert" className="rounded-2xl border border-line bg-panel p-6 text-mist">{error}</p>;
  // Show a loading message until the profile arrives.
  if (!profile) return <p role="status" className="rounded-2xl border border-line bg-panel p-6 text-mist/70">Loading your profile…</p>;

  // Draw the page.
  return (
    // Keep the page a comfortable reading width.
    <div className="mx-auto max-w-2xl space-y-6">
      {/* The way back to the dashboard. */}
      <Link to="/student" className="text-sm text-sage underline underline-offset-4 hover:text-sage-light">← My progress</Link>
      {/* The heading, with the Edit button while viewing. */}
      <header className="flex flex-wrap items-center justify-between gap-4">
        {/* The page's title. */}
        <h1 className="font-display text-3xl font-bold text-white">{form ? "Edit profile" : "My profile"}</h1>
        {/* Switches to the form. */}
        {!form && <button type="button" onClick={startEditing} className="rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink hover:bg-sage-light">Edit profile</button>}
      </header>
      {/* Any error while viewing, such as a picture that's too large. */}
      {!form && error && <p role="alert" className="rounded-xl border border-amber-300/30 p-4 text-sm text-amber-200">{error}</p>}

      {/* The picture and its buttons. */}
      <section aria-label="Profile picture" className="flex flex-wrap items-center gap-5 rounded-2xl border border-line bg-panel p-5 sm:p-6">
        {/* The large picture or initials. */}
        <Avatar name={profile.full_name} version={user.picture_version} className="h-24 w-24 text-2xl" />
        {/* The buttons and the limits. */}
        <div>
          {/* The two buttons. */}
          <div className="flex flex-wrap items-center gap-3">
            {/* A label styled as a button, which opens the file chooser. The real input is hidden but still usable by keyboard. */}
            <label className={`rounded-lg border border-sage/40 bg-sage/10 px-4 py-2 text-sm font-medium text-sage focus-within:outline-2 focus-within:outline-sage hover:bg-sage/20 ${pictureBusy ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}>
              {/* The button's text. */}
              {pictureBusy ? "Saving…" : profile.has_picture ? "Change picture" : "Add picture"}
              {/* The browser's file chooser, showing only allowed types. */}
              <input type="file" accept=".png,.jpg,.jpeg" disabled={pictureBusy} onChange={choosePicture} className="sr-only" />
            </label>
            {/* Remove only shows when there's a picture. */}
            {profile.has_picture && <button type="button" disabled={pictureBusy} onClick={() => setConfirmingRemove(true)} className="rounded-lg border border-line px-4 py-2 text-sm text-mist hover:border-sage hover:text-white disabled:opacity-50">Remove</button>}
          </div>
          {/* The limits. */}
          <p className="mt-2 text-xs text-mist/60">PNG or JPG, up to 2 MB.</p>
        </div>
      </section>
      {/* The "are you sure?" box, while a removal is waiting to be confirmed. */}
      {confirmingRemove && <ConfirmDialog title="Remove your profile picture?" confirmLabel="Remove" onConfirm={confirmRemovePicture} onCancel={() => setConfirmingRemove(false)} />}

      {/* View mode shows the details. */}
      {!form && (
        // The details card.
        <dl className="rounded-2xl border border-line bg-panel p-5 sm:p-6">
          {/* The name. */}
          <Detail label="Full name">{profile.full_name}</Detail>
          {/* The login email. */}
          <Detail label="Email">{profile.email}</Detail>
          {/* What they research. */}
          <Detail label="Research interests">{profile.research_interests}</Detail>
          {/* Their lab or research group. */}
          <Detail label="Lab or research group">{profile.lab_name}</Detail>
          {/* The education background. */}
          <Detail label="Education">{profile.education}</Detail>
          {/* The biography. */}
          <Detail label="Bio">{profile.bio}</Detail>
          {/* Each link, opening in a new tab. The backend only allows web links. */}
          {LINK_FIELDS.map((field) => <Detail key={field.name} label={field.label}>{profile[field.name] && <a href={profile[field.name]} target="_blank" rel="noopener noreferrer" className="text-sage underline underline-offset-4 hover:text-sage-light">{profile[field.name]}</a>}</Detail>)}
        </dl>
      )}

      {/* The program details come from the student's record, so they show in both view and edit modes. */}
      <section aria-labelledby="program-heading" className="rounded-2xl border border-line bg-panel p-5 sm:p-6">
        {/* The section's heading. */}
        <h2 id="program-heading" className="font-display text-lg font-semibold text-white">Program details</h2>
        {/* Explain why these can't be edited. */}
        <p className="mt-1 text-xs text-mist/60">These come from your program record, so you can't edit them here.</p>
        {/* The details. */}
        <dl className="mt-4">
          {/* The research advisor. */}
          <Detail label="Research advisor">{profile.advisor_name}</Detail>
          {/* When they started. */}
          <Detail label="Started">{profile.start_term && profile.start_year ? `${profile.start_term === "fall" ? "Fall" : "Spring"} ${profile.start_year}` : null}</Detail>
          {/* Full-time or part-time. */}
          <Detail label="Enrollment">{profile.enrollment_status === "full_time" ? "Full-time" : profile.enrollment_status === "part_time" ? "Part-time" : null}</Detail>
          {/* Advanced standing. An unknown value stays empty. */}
          <Detail label="Advanced standing">{profile.advanced_standing === null ? null : profile.advanced_standing ? "Yes" : "No"}</Detail>
        </dl>
      </section>

      {/* Edit mode shows the form. */}
      {form && (
        // The form card.
        <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-sage/40 bg-panel p-5 sm:p-6">
          {/* The name. */}
          <label className="block text-sm text-mist">
            {/* The label's text. */}
            Full name
            {/* The name can't be empty. */}
            <input type="text" required maxLength={255} value={form.full_name} onChange={(event) => setField("full_name", event.target.value)} className={FIELD} />
          </label>
          {/* The email, which is shown but can't be changed. */}
          <label className="block text-sm text-mist">
            {/* The label's text. */}
            Email (used to log in, can't be changed here)
            {/* A read-only box. */}
            <input type="email" value={profile.email} disabled className={`${FIELD} opacity-60`} />
          </label>
          {/* What they research. */}
          <label className="block text-sm text-mist">
            {/* The label's text. */}
            Research interests
            {/* An optional longer answer. */}
            <textarea rows={2} maxLength={2000} placeholder="e.g. Databases, machine learning" value={form.research_interests} onChange={(event) => setField("research_interests", event.target.value)} className={FIELD} />
          </label>
          {/* Their lab or research group. */}
          <label className="block text-sm text-mist">
            {/* The label's text. */}
            Lab or research group
            {/* An optional short answer. */}
            <input type="text" maxLength={255} value={form.lab_name} onChange={(event) => setField("lab_name", event.target.value)} className={FIELD} />
          </label>
          {/* The education background. */}
          <label className="block text-sm text-mist">
            {/* The label's text. */}
            Education
            {/* An optional longer answer. */}
            <textarea rows={3} maxLength={2000} placeholder="e.g. MS in Computer Science, University at Albany, 2024" value={form.education} onChange={(event) => setField("education", event.target.value)} className={FIELD} />
          </label>
          {/* The biography. */}
          <label className="block text-sm text-mist">
            {/* The label's text. */}
            Bio
            {/* An optional longer answer. */}
            <textarea rows={4} maxLength={2000} value={form.bio} onChange={(event) => setField("bio", event.target.value)} className={FIELD} />
          </label>
          {/* One box for each link. */}
          {LINK_FIELDS.map((field) => (
            // The field's label.
            <label key={field.name} className="block text-sm text-mist">
              {/* The label's text. */}
              {field.label}
              {/* An optional web address, which the browser also checks. */}
              <input type="url" maxLength={500} placeholder={field.placeholder} value={form[field.name]} onChange={(event) => setField(field.name, event.target.value)} className={FIELD} />
            </label>
          ))}
          {/* Any error, such as an invalid link. */}
          {error && <p role="alert" className="text-sm text-amber-200">{error}</p>}
          {/* The form's buttons. */}
          <div className="flex justify-end gap-3">
            {/* Goes back to viewing without saving. */}
            <button type="button" onClick={cancelEditing} className="rounded-lg border border-line px-4 py-2 text-sm text-mist hover:border-sage hover:text-white">Cancel</button>
            {/* Saves the form. */}
            <button type="submit" disabled={saving} className="rounded-lg bg-sage px-5 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50">{saving ? "Saving…" : "Save profile"}</button>
          </div>
        </form>
      )}
    </div>
  );
}
