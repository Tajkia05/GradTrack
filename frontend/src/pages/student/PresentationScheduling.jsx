// PresentationScheduling.jsx — THE PRESENTATION PART OF THE SUBMISSION POPUP.
// The student proposes 1 to 3 dates after uploading their document, sees the committee's answers, and can cancel.

// useState remembers values on the page.
import { useState } from "react";
// api talks to the backend.
import { api } from "../../api/client.js";
// Shows a short success message.
import { useToast } from "../../components/Toast.jsx";
// The app's own "Are you sure?" box.
import ConfirmDialog from "../../components/ConfirmDialog.jsx";

// The most dates a student can propose, matching the backend.
const MAX_DATES = 3;
// The text shown for each presentation status.
export const PRESENTATION_LABELS = { awaiting_availability: "Waiting for committee availability", needs_new_dates: "New dates needed", scheduled: "Presentation scheduled", held: "Presentation held" };
// The text shown for each way of presenting.
const MODE_LABELS = { in_person: "In person", online: "Online (Zoom)", hybrid: "Both: in person + Zoom" };
// How a committee member joins, shown next to their answer.
const JOIN_LABELS = { in_person: "in person", online: "Zoom" };

// The times a student can pick: every half hour from 8:00 AM to 6:00 PM, as "HH:mm" text.
const TIME_CHOICES = Array.from({ length: 21 }, (_, step) => `${String(8 + Math.floor(step / 2)).padStart(2, "0")}:${step % 2 ? "30" : "00"}`);

// Shows "HH:mm" text as a readable time, e.g. "2:30 PM".
function timeLabel(time) {
  // Split the hours and minutes.
  const [hours, minutes] = time.split(":").map(Number);
  // Use the 12-hour clock with AM or PM.
  return `${hours % 12 || 12}:${String(minutes).padStart(2, "0")} ${hours < 12 ? "AM" : "PM"}`;
}

// Shows a date and time in a readable way, e.g. "Thu, Nov 20, 2026, 2:00 PM".
export function formatWhen(value) {
  // Use the viewer's own time zone.
  return new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

// Turns a date into the "YYYY-MM-DDTHH:mm" text the date picker uses, in the viewer's time zone.
function toPickerValue(value) {
  // Read the date.
  const moment = new Date(value);
  // Pads a number to two digits.
  const pad = (number) => String(number).padStart(2, "0");
  // Build the text from the local date and time.
  return `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}T${pad(moment.getHours())}:${pad(moment.getMinutes())}`;
}

// A meeting link that opens in a new tab. The backend checked it starts with http.
function MeetingLink({ href }) {
  // Show the link itself.
  return <a href={href} target="_blank" rel="noopener noreferrer" className="break-all text-sage underline underline-offset-4 hover:text-sage-light">{href}</a>;
}

// Shows the location: the room, the link, or both for a hybrid presentation.
function Location({ presentation }) {
  // An online presentation's location is its link.
  if (presentation.mode === "online") return <MeetingLink href={presentation.location} />;
  // A hybrid has a room and a Zoom link.
  if (presentation.mode === "hybrid") return <><span className="text-white">{presentation.location}</span> · Zoom: <MeetingLink href={presentation.meeting_link} /></>;
  // In person shows the room.
  return <span className="text-white">{presentation.location}</span>;
}

// One answer, e.g. "✓ Omar Haddad (Zoom)". The way of joining shows when it matters: in a hybrid, or when it doesn't match.
function answerText(response, mode) {
  // Show the way of joining for someone attending, in a hybrid or when it differs from the presentation's.
  const join = response.available && response.attend_mode && (mode === "hybrid" || response.attend_mode !== mode) ? ` (${JOIN_LABELS[response.attend_mode]})` : "";
  // A tick or a cross, the name, and the way of joining.
  return `${response.available ? "✓" : "✗"} ${response.name}${join}`;
}

// The current presentation: its status, dates, answers, the choose buttons and the cancel button.
function PresentationDetails({ presentation, onCancel, cancelling, onChoose, choosing }) {
  // True if it can still be cancelled: waiting, or scheduled and not yet held.
  const cancellable = presentation.status === "awaiting_availability" || presentation.status === "scheduled";
  // Draw the details.
  return (
    // The box.
    <div className="rounded-xl border border-line bg-ink/40 p-4 text-sm">
      {/* The status. */}
      <p className="font-semibold text-white">{PRESENTATION_LABELS[presentation.status] ?? presentation.status}{presentation.attempt > 1 ? ` · attempt ${presentation.attempt}` : ""}</p>
      {/* The confirmed date, once there is one. */}
      {presentation.scheduled_at && <p className="mt-1 text-sage">{formatWhen(presentation.scheduled_at)}</p>}
      {/* How and where. */}
      <p className="mt-1 text-mist/80">{MODE_LABELS[presentation.mode]}: <Location presentation={presentation} /></p>
      {/* The proposed dates and answers, until a date is confirmed. */}
      {!presentation.scheduled_at && (
        // The list of dates.
        <ul className="mt-3 space-y-2">
          {/* One row for each date. */}
          {presentation.options.map((option) => (
            // The row, highlighted when the whole committee can attend.
            <li key={option.id} className={`rounded-lg border px-3 py-2 ${option.everyone_available ? "border-sage bg-sage/10" : "border-line"}`}>
              {/* The date, with a label when everyone can attend. */}
              <p className="text-white">{formatWhen(option.starts_at)}{option.everyone_available && <span className="ml-2 font-semibold text-sage">Everyone can attend</span>}</p>
              {/* The answers so far, or a note that there are none. */}
              <p className="mt-1 text-mist/70">{option.responses.length > 0
                // Each person with a tick or a cross.
                ? option.responses.map((response) => answerText(response, presentation.mode)).join(" · ")
                // Nobody has answered yet.
                : "No answers yet"}</p>
              {/* Who still needs to answer. */}
              {option.waiting_for.length > 0 && <p className="mt-1 text-mist/60">Waiting for: {option.waiting_for.join(", ")}</p>}
              {/* The student chooses a date everyone can attend. */}
              {option.everyone_available && presentation.status === "awaiting_availability" && <button type="button" onClick={() => onChoose(option)} disabled={choosing} className="mt-2 rounded-lg bg-sage px-3 py-1.5 font-semibold text-ink hover:bg-sage-light disabled:opacity-50">{choosing ? "Saving…" : "Choose this date"}</button>}
            </li>
          ))}
        </ul>
      )}
      {/* The cancel button, before the date. */}
      {cancellable && <button type="button" onClick={onCancel} disabled={cancelling} className="mt-3 rounded-lg border border-amber-300/40 px-3 py-1.5 text-amber-200 hover:bg-amber-300/10 disabled:opacity-50">{cancelling ? "Cancelling…" : "Cancel presentation"}</button>}
    </div>
  );
}

// The form for proposing dates.
function ProposeForm({ data, onUpdate }) {
  // The presentation part of the popup data.
  const state = data.presentation;
  // In person, online or both.
  const [mode, setMode] = useState("in_person");
  // The room, or the link for online.
  const [location, setLocation] = useState("");
  // The Zoom link for a hybrid presentation.
  const [meetingLink, setMeetingLink] = useState("");
  // The chosen dates, each a day ("YYYY-MM-DD") and a time ("HH:mm"). Starts with one empty date.
  const [dates, setDates] = useState([{ day: "", time: "" }]);
  // For each date's position, the external members who can attend and how: { memberId: "in_person" or "online" }.
  const [externals, setExternals] = useState({});
  // An error message to show. Empty when there's no error.
  const [error, setError] = useState("");
  // True while sending, to prevent double clicks.
  const [saving, setSaving] = useState(false);
  // Shows a short success message.
  const showToast = useToast();
  // The earliest allowed moment, split into its day and time, e.g. ["2026-11-18", "20:34"].
  const [earliestDay, earliestTime] = state.earliest_at ? toPickerValue(state.earliest_at).split("T") : [undefined, undefined];

  // Changes one date's day or time.
  function setDate(index, field, value) {
    // Replace only that part of that date.
    setDates((current) => current.map((date, position) => (position === index ? { ...date, [field]: value } : date)));
  }

  // Finds an earlier date with the same day and time, and returns its position, or -1 if there's none.
  function sameAs(index) {
    // This date.
    const { day, time } = dates[index];
    // Only a complete date can repeat another.
    if (!day || !time) return -1;
    // Look only at the dates above it.
    return dates.findIndex((other, position) => position < index && other.day === day && other.time === time);
  }

  // True if a time can't be picked for a date: it's too early, or another date already has that day and time.
  function timeTaken(index, time) {
    // This date's day.
    const { day } = dates[index];
    // On the earliest day, times before the earliest allowed time are too early.
    if (day && day === earliestDay && time < earliestTime) return true;
    // Another date already uses this day and time.
    return dates.some((other, position) => position !== index && day && other.day === day && other.time === time);
  }

  // True if any two dates have the same day and time.
  const hasRepeat = dates.some((_, index) => sameAs(index) !== -1);

  // Removes one date, and its ticked members.
  function removeDate(index) {
    // Remove it from the list.
    setDates((current) => current.filter((_, position) => position !== index));
    // Move the later dates' ticks up by one.
    setExternals((current) => Object.fromEntries(Object.entries(current).filter(([position]) => Number(position) !== index)
      // Shift each later position down.
      .map(([position, ids]) => [Number(position) > index ? Number(position) - 1 : Number(position), ids])));
  }

  // Sets how an external member attends one date: "in_person", "online", or "" if they can't.
  function setExternal(index, memberId, value) {
    // Update that date's answers.
    setExternals((current) => {
      // Copy this date's answers so far.
      const answers = { ...(current[index] ?? {}) };
      // Remove the member if they can't attend.
      if (!value) delete answers[memberId];
      // Otherwise record how they'll join.
      else answers[memberId] = value;
      // Save the date's answers.
      return { ...current, [index]: answers };
    });
  }

  // Runs when the form is submitted.
  async function handleSubmit(event) {
    // Stop the browser from reloading the page.
    event.preventDefault();
    // Clear any old error.
    setError("");
    // The same day and time can't be proposed twice.
    if (hasRepeat) {
      // Explain what to change.
      setError("Each date must have a different day or time.");
      // Don't send anything.
      return;
    }
    // Disable the button while this runs.
    setSaving(true);
    // Try to send the dates.
    try {
      // Each date as a moment in time, with the external members who can attend, and those joining by Zoom in a hybrid.
      const options = dates.map((date, index) => {
        // This date's external answers.
        const answers = Object.entries(externals[index] ?? {});
        // Build the date.
        return { starts_at: new Date(`${date.day}T${date.time}`).toISOString(), external_member_ids: answers.map(([id]) => Number(id)),
          // Only a hybrid separates Zoom from in person.
          external_online_ids: mode === "hybrid" ? answers.filter(([, how]) => how === "online").map(([id]) => Number(id)) : [] };
      });
      // Send them, with the Zoom link only for a hybrid, and show the updated data from the backend.
      onUpdate(await api(`/students/me/milestones/${data.milestone_id}/presentation`, { method: "POST", body: JSON.stringify({ mode, location, meeting_link: mode === "hybrid" ? meetingLink : null, options }) }));
      // Confirm it.
      showToast("Your presentation dates were sent to your committee.");
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

  // Draw the form.
  return (
    // The form.
    <form onSubmit={handleSubmit} aria-labelledby="presentation-form-heading" className="rounded-xl border border-line p-4 text-sm">
      {/* The heading. */}
      <h4 id="presentation-form-heading" className="font-display font-semibold text-white">Propose presentation dates</h4>
      {/* The earliest allowed date. */}
      {state.earliest_at && <p className="mt-1 text-mist/70">Choose up to {MAX_DATES} dates on or after {formatWhen(state.earliest_at)}.</p>}
      {/* In person or online. */}
      <fieldset className="mt-3">
        {/* The group's label. */}
        <legend className="text-mist">How will you present?</legend>
        {/* The choices side by side, wrapping on small screens. */}
        <div className="mt-2 flex flex-wrap gap-4">
          {/* One radio button per choice. */}
          {Object.entries(MODE_LABELS).map(([value, label]) => (
            // The choice and its label.
            <label key={value} className="flex items-center gap-2 text-white">
              {/* The radio button. */}
              <input type="radio" name="presentation-mode" value={value} checked={mode === value} onChange={() => setMode(value)} className="accent-sage" />
              {/* The choice's text. */}
              {label}
            </label>
          ))}
        </div>
      </fieldset>
      {/* The room or link. */}
      <label className="mt-3 block text-mist">
        {/* The label changes with the choice. */}
        {mode === "online" ? "Zoom link" : "Room"}
        {/* The text box. A link box checks the format for online. */}
        <input type={mode === "online" ? "url" : "text"} required maxLength={255} value={location} onChange={(event) => setLocation(event.target.value)} placeholder={mode === "online" ? "https://…" : "e.g. Room 1234, Science Library"} className="mt-1 block w-full rounded-lg border border-line bg-ink px-3 py-2 text-white" />
      </label>
      {/* A hybrid also needs the Zoom link. */}
      {mode === "hybrid" && (
        // The link box.
        <label className="mt-3 block text-mist">
          {/* The label. */}
          Zoom link, for those joining online
          {/* The link box checks the format. */}
          <input type="url" required maxLength={255} value={meetingLink} onChange={(event) => setMeetingLink(event.target.value)} placeholder="https://…" className="mt-1 block w-full rounded-lg border border-line bg-ink px-3 py-2 text-white" />
        </label>
      )}
      {/* The dates. */}
      <div className="mt-3 space-y-3">
        {/* One block per date. */}
        {dates.map((date, index) => (
          // The date's block.
          <div key={index} className="rounded-lg border border-line p-3">
            {/* The heading and remove button. */}
            <div className="flex items-center justify-between gap-2">
              {/* The date's number. */}
              <p className="text-mist">Date {index + 1}</p>
              {/* Remove this date, when there's more than one. */}
              {dates.length > 1 && <button type="button" onClick={() => removeDate(index)} aria-label={`Remove date ${index + 1}`} className="rounded-lg border border-line px-3 py-1 text-mist hover:border-sage">Remove</button>}
            </div>
            {/* The day and the time side by side, stacked on small screens. */}
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {/* The day picker with its label. */}
              <label className="text-mist/70">
                {/* The label. */}
                Day
                {/* The picker, starting at the earliest allowed day. */}
                <input type="date" required min={earliestDay} value={date.day} onChange={(event) => setDate(index, "day", event.target.value)} className="mt-1 block w-full rounded-lg border border-line bg-ink px-3 py-2 text-white scheme-dark" />
              </label>
              {/* The time list with its label. */}
              <label className="text-mist/70">
                {/* The label. */}
                Time
                {/* The list of half-hour times. */}
                <select required value={date.time} onChange={(event) => setDate(index, "time", event.target.value)} className="mt-1 block w-full rounded-lg border border-line bg-ink px-3 py-2 text-white">
                  {/* Shown until a time is picked. */}
                  <option value="" disabled>Choose a time</option>
                  {/* One choice per half hour, greyed out when it's too early or another date already has it. */}
                  {TIME_CHOICES.map((time) => <option key={time} value={time} disabled={timeTaken(index, time)}>{timeLabel(time)}</option>)}
                </select>
              </label>
            </div>
            {/* A warning when this date repeats an earlier one, such as after changing its day. */}
            {sameAs(index) !== -1 && <p role="alert" className="mt-2 text-amber-200">Date {sameAs(index) + 1} already has this day and time. Choose a different time.</p>}
            {/* The external members, whose answers the student enters. */}
            {state.external_members.length > 0 && (
              // The checkboxes.
              <fieldset className="mt-2">
                {/* The group's label. */}
                <legend className="text-mist/70">External members who can attend</legend>
                {/* One row per member: a choice of how they join for a hybrid, or a checkbox otherwise. */}
                {state.external_members.map((member) => mode === "hybrid" ? (
                  // The member's name and choice.
                  <label key={member.id} className="mt-1 flex items-center justify-between gap-2 text-white">
                    {/* The member's name. */}
                    {member.name}
                    {/* Can't attend, in person, or Zoom. */}
                    <select value={externals[index]?.[member.id] ?? ""} onChange={(event) => setExternal(index, member.id, event.target.value)} className="rounded-lg border border-line bg-ink px-2 py-1 text-white">
                      {/* They can't attend. */}
                      <option value="">Can't attend</option>
                      {/* In the room. */}
                      <option value="in_person">In person</option>
                      {/* By Zoom. */}
                      <option value="online">Zoom</option>
                    </select>
                  </label>
                ) : (
                  // The checkbox and name.
                  <label key={member.id} className="mt-1 flex items-center gap-2 text-white">
                    {/* Ticked means they can attend, in the presentation's own way. */}
                    <input type="checkbox" checked={Boolean(externals[index]?.[member.id])} onChange={(event) => setExternal(index, member.id, event.target.checked ? mode : "")} className="accent-sage" />
                    {/* The member's name. */}
                    {member.name}
                  </label>
                ))}
              </fieldset>
            )}
          </div>
        ))}
      </div>
      {/* Add another date, up to the limit. */}
      {dates.length < MAX_DATES && <button type="button" onClick={() => setDates((current) => [...current, { day: "", time: "" }])} className="mt-3 text-sage underline underline-offset-4 hover:text-sage-light">Add another date</button>}
      {/* Any error, such as a date that's too early. */}
      {error && <p role="alert" className="mt-3 text-amber-200">{error}</p>}
      {/* Sends the dates. */}
      <div><button type="submit" disabled={saving || hasRepeat} className="mt-4 rounded-lg bg-sage px-4 py-2 font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50">{saving ? "Sending…" : "Send dates to committee"}</button></div>
    </form>
  );
}

// The whole presentation section of the popup.
export default function PresentationScheduling({ data, onUpdate }) {
  // The presentation part of the popup data.
  const state = data.presentation;
  // The current presentation, leaving out a cancelled one.
  const presentation = state.presentation?.status === "cancelled" ? null : state.presentation;
  // An error from cancelling.
  const [error, setError] = useState("");
  // True while cancelling, to prevent double clicks.
  const [cancelling, setCancelling] = useState(false);
  // True while saving the chosen date, to prevent double clicks.
  const [choosing, setChoosing] = useState(false);
  // The question waiting for an answer: { option } to choose a date, { cancel: true } to cancel, or null for none.
  const [asking, setAsking] = useState(null);
  // Shows a short success message.
  const showToast = useToast();

  // Runs when the student confirms the chosen date.
  async function handleChoose(option) {
    // Close the question.
    setAsking(null);
    // Clear any old error.
    setError("");
    // Disable the buttons while this runs.
    setChoosing(true);
    // Try to save it.
    try {
      // Save the date, and show the updated data from the backend.
      onUpdate(await api(`/students/me/milestones/${data.milestone_id}/presentation/date`, { method: "PUT", body: JSON.stringify({ option_id: option.id }) }));
      // Confirm it.
      showToast("Your presentation is scheduled, and your committee has been informed.");
    // The backend refused or couldn't be reached.
    } catch (err) {
      // Show the message.
      setError(err.message);
    // Runs whether it worked or not.
    } finally {
      // Enable the buttons again.
      setChoosing(false);
    }
  }

  // Runs when the student confirms the cancellation.
  async function handleCancel() {
    // Close the question.
    setAsking(null);
    // Clear any old error.
    setError("");
    // Disable the button while this runs.
    setCancelling(true);
    // Try to cancel.
    try {
      // Cancel, and show the updated data from the backend.
      onUpdate(await api(`/students/me/milestones/${data.milestone_id}/presentation`, { method: "DELETE" }));
      // Confirm it.
      showToast("Your presentation was cancelled.");
    // The backend refused or couldn't be reached.
    } catch (err) {
      // Show the message.
      setError(err.message);
    // Runs whether it worked or not.
    } finally {
      // Enable the button again.
      setCancelling(false);
    }
  }

  // Nothing to show before the document is uploaded, or after the decision.
  if (!presentation && !state.can_propose && !state.message) return null;
  // Draw the section.
  return (
    // The section.
    <section aria-labelledby="presentation-heading" className="space-y-3">
      {/* The heading. */}
      <h3 id="presentation-heading" className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">Presentation</h3>
      {/* What to do next, or why the student has to wait. */}
      {state.message && <p className="text-sm text-mist">{state.message}</p>}
      {/* The current presentation. */}
      {/* The buttons ask first, using the app's own box. */}
      {presentation && <PresentationDetails presentation={presentation} onCancel={() => setAsking({ cancel: true })} cancelling={cancelling} onChoose={(option) => setAsking({ option })} choosing={choosing} />}
      {/* Asks before scheduling the chosen date. */}
      {asking?.option && <ConfirmDialog title={`Schedule your presentation for ${formatWhen(asking.option.starts_at)}?`} message="Your advisor and committee members will be notified." confirmLabel="Schedule" onConfirm={() => handleChoose(asking.option)} onCancel={() => setAsking(null)} />}
      {/* Asks before cancelling. */}
      {asking?.cancel && <ConfirmDialog title="Cancel this presentation?" message="Your advisor and committee members will be notified, and you'll need to propose new dates." confirmLabel="Cancel presentation" onConfirm={handleCancel} onCancel={() => setAsking(null)} />}
      {/* An error from cancelling or choosing. */}
      {error && <p role="alert" className="text-sm text-amber-200">{error}</p>}
      {/* The form, when dates can be proposed. */}
      {state.can_propose && <ProposeForm data={data} onUpdate={onUpdate} />}
    </section>
  );
}
