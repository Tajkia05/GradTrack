// Coursework.jsx — THE BUTTON AND POPUP FOR SELECTING COURSES AND SEEING CREDIT PROGRESS.
// It sits on the dashboard's Coursework card. All credit calculations come from the backend, so the rules live in one place.

// useEffect runs code when something changes, useRef keeps a value between draws, and useState remembers values on the page.
import { useEffect, useRef, useState } from "react";
// api is the one function that talks to the backend.
import { api } from "../../api/client.js";
// The app's own "are you sure?" box.
import ConfirmDialog from "../../components/ConfirmDialog.jsx";

// The grades a student can select, matching the backend's list.
const GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E", "S", "U"];
// The dropdown's headings in order, with each group's value from the backend. null is for courses with no group.
const COURSE_GROUPS = [
  { area: "core", label: "Core" }, // Only CSI 503 and CSI 790.
  { area: "theory", label: "Breadth: Theoretical CS" }, // One course from this list is required.
  { area: "ai_ml", label: "Breadth: AI & ML" }, // One course from this list is required.
  { area: "systems", label: "Breadth: Systems or CSI 518" }, // One course from this list is required.
  { area: "dissertation", label: "Dissertation research" }, // Only CSI 898.
  { area: null, label: "Other courses (electives)" }, // Every other course on the list.
];
// The same styling for every dropdown and input on the form.
const FIELD = "mt-1 w-full rounded-lg border border-line bg-ink px-3 py-2 text-sm text-white focus:border-sage focus:outline-none";

// Works out where a semester is today, using the same dates as the backend: Spring is Jan 1 to May 31, Fall is Jun 1 to Dec 31.
function semesterStatus(term, year) {
  // True for the Spring term.
  const isSpring = term === "spring";
  // The semester's first day.
  const start = new Date(year, isSpring ? 0 : 5, 1);
  // The semester's last day.
  const end = new Date(year, isSpring ? 4 : 11, 31);
  // Today's date and time.
  const now = new Date();
  // Started and ended are true from the start of those days. endLabel is the date shown to the student.
  return { started: now >= start, ended: now >= end, endLabel: isSpring ? `May 31, ${year}` : `December 31, ${year}` };
}

// Returns an empty form, set to the running semester.
function emptyForm() {
  // Today's date and time.
  const now = new Date();
  // Grade "" means the course is still in progress. Months count from 0, so 0 to 4 is January to May, which is Spring.
  return { course_id: "", credits: "", term: now.getMonth() <= 4 ? "spring" : "fall", year: now.getFullYear(), grade: "", is_manual: false, manual_code: "", manual_title: "", manual_department: "", manual_is_research: false };
}

// Draws one labeled progress bar.
function ProgressBar({ name, earned, required }) {
  // Work out how full the bar is, as a percentage.
  const percent = Math.round((earned * 100) / required);
  // Return the bar's HTML.
  return (
    // The bar's outer container.
    <div>
      {/* The group's name on the left, and its credits on the right. */}
      <div className="flex justify-between gap-3 text-sm">
        {/* The group's name. */}
        <span className="text-mist">{name}</span>
        {/* The credits earned out of the credits needed. */}
        <span className="shrink-0 text-mist/70">{earned} of {required} credits</span>
      </div>
      {/* The empty track, with its value exposed to screen readers. */}
      <div role="progressbar" aria-label={name} aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} className="mt-2 h-2 overflow-hidden rounded-full bg-ink">
        {/* The filled part of the track. */}
        <div className="h-full rounded-full bg-sage" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

// One box that opens the course list when clicked, and filters it by code or name when typed in.
function CourseDropdown({ courses, value, onSelect }) {
  // The text typed in the box.
  const [text, setText] = useState("");
  // True while the list is showing.
  const [open, setOpen] = useState(false);
  // The position of the option highlighted by the arrow keys.
  const [activeIndex, setActiveIndex] = useState(0);
  // The currently selected course, if any.
  const selected = courses.find((course) => String(course.id) === value);
  // The text shown in the box when a course is selected.
  const selectedLabel = selected ? `${selected.code} — ${selected.title}` : "";
  // Prepares text for searching: lowercase with no spaces, so "csi503" finds "CSI 503".
  const normalize = (input) => input.toLowerCase().replace(/\s/g, "");
  // Build each heading with its matching courses, leaving out any heading with no matches.
  const groups = COURSE_GROUPS
    // Keep the courses in this group whose code or name contains the typed text.
    .map((group) => ({ ...group, courses: courses.filter((course) => course.area === group.area && normalize(`${course.code} ${course.title}`).includes(normalize(text))) }))
    // Remove the empty headings.
    .filter((group) => group.courses.length > 0);
  // All the matching courses in display order, for the arrow keys.
  const options = groups.flatMap((group) => group.courses);

  // Keep the highlighted option visible when the arrow keys move past the edge of the list.
  useEffect(() => {
    // Find the highlighted option on the page and scroll to it, if the list is showing.
    if (open) document.getElementById(`course-option-${activeIndex}`)?.scrollIntoView({ block: "nearest" });
  // Run this whenever the highlight moves or the list opens.
  }, [open, activeIndex]);

  // Shows the whole list, with the first course highlighted.
  function openList() {
    // Clear the typed text, so every course is listed.
    setText("");
    // Highlight the first option.
    setActiveIndex(0);
    // Show the list.
    setOpen(true);
  }

  // Selects a course and closes the list.
  function choose(course) {
    // Tell the form which course was picked.
    onSelect(String(course.id));
    // Clear the typed text.
    setText("");
    // Hide the list.
    setOpen(false);
  }

  // Handles the arrow, Enter and Escape keys.
  function handleKeyDown(event) {
    // The down arrow moves the highlight down, stopping at the last option.
    if (event.key === "ArrowDown") {
      // Stop the cursor from moving in the box.
      event.preventDefault();
      // Open the list if it's closed, otherwise move the highlight.
      if (open) setActiveIndex((index) => Math.min(index + 1, options.length - 1)); else openList();
    // The up arrow moves the highlight up, stopping at the first option.
    } else if (event.key === "ArrowUp" && open) {
      // Stop the cursor from moving in the box.
      event.preventDefault();
      // Move the highlight.
      setActiveIndex((index) => Math.max(index - 1, 0));
    // Enter selects the highlighted course.
    } else if (event.key === "Enter") {
      // Stop Enter from submitting the form.
      event.preventDefault();
      // Select the highlighted course, if the list is showing one.
      if (open && options[activeIndex]) choose(options[activeIndex]);
    // Escape closes the list, without closing the popup.
    } else if (event.key === "Escape" && open) {
      // Stop the popup from closing as well.
      event.preventDefault();
      // Clear the typed text.
      setText("");
      // Hide the list.
      setOpen(false);
    }
  }

  // Keeps a running count, so each option gets its position in the full list.
  let position = -1;
  // Draw the box and the list.
  return (
    // "relative" lets the list sit just under the box, across the full form width.
    <div className="relative sm:col-span-2">
      {/* The box's label. */}
      <label className="text-sm text-mist">
        {/* The label's text. */}
        Course
        {/* While open it shows the typed text, and while closed it shows the selected course. */}
        <input
          // A plain text box, set up to act as a dropdown.
          type="text"
          // Tells screen readers this box controls a list.
          role="combobox"
          // Tells screen readers whether the list is showing.
          aria-expanded={open}
          // Links the box to its list.
          aria-controls="course-options"
          // Tells screen readers which option is highlighted.
          aria-activedescendant={open && options[activeIndex] ? `course-option-${activeIndex}` : undefined}
          // Turns off the browser's own suggestions, which would cover the list.
          autoComplete="off"
          // The form can't be submitted until a course is selected.
          required
          // Show the typed text while open, and the selected course while closed.
          value={open ? text : selectedLabel}
          // A hint, which keeps showing the selected course while the student types.
          placeholder={selectedLabel || "Select or type a course code or name"}
          // Clicking or tabbing into the box opens the list.
          onFocus={openList}
          // Clicking again after a course was selected reopens the list.
          onClick={() => { if (!open) openList(); }}
          // Typing filters the list, and highlights the first match.
          onChange={(event) => { setText(event.target.value); setActiveIndex(0); setOpen(true); }}
          // Handle the arrow, Enter and Escape keys.
          onKeyDown={handleKeyDown}
          // Leaving the box closes the list and clears the typed text.
          onBlur={() => { setOpen(false); setText(""); }}
          // The same styling as the other fields, with room for the arrow.
          className={`${FIELD} pr-8`}
        />
      </label>
      {/* The small arrow inside the box, which is only decoration. */}
      <span aria-hidden="true" className="pointer-events-none absolute right-3 top-8 text-mist/50">⌄</span>
      {/* The list, only while it's open. Pressing on it doesn't take the cursor out of the box. */}
      {open && (
        // The list floats over the fields below it, and scrolls if it's long.
        <ul id="course-options" role="listbox" aria-label="Courses" onMouseDown={(event) => event.preventDefault()} className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-line bg-ink py-1 text-sm shadow-xl">
          {/* A message when nothing matches. */}
          {options.length === 0 && <li className="px-3 py-2 text-amber-200">No courses match. If it's a UAlbany course, tick the box above to enter it manually.</li>}
          {/* One heading and its courses for each group. */}
          {groups.map((group) => [
            // The heading, which can't be selected.
            <li key={group.label} role="presentation" className="px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wider text-mist/50">{group.label}</li>,
            // The group's courses.
            ...group.courses.map((course) => {
              // Move the running count on to this option.
              position += 1;
              // Remember this option's position for its click and hover actions.
              const index = position;
              // Draw the option, highlighted if the arrow keys or mouse are on it.
              return <li key={course.id} id={`course-option-${index}`} role="option" aria-selected={String(course.id) === value} onMouseEnter={() => setActiveIndex(index)} onClick={() => choose(course)} className={`cursor-pointer px-3 py-2 text-white ${index === activeIndex ? "bg-sage/20" : ""}`}>{course.code} — {course.title}</li>;
            }),
          ])}
        </ul>
      )}
    </div>
  );
}

// The popup's content. It receives the data from the backend, and a function that stores updated data.
function CourseworkContent({ data, onUpdate }) {
  // The current values in the form.
  const [form, setForm] = useState(emptyForm());
  // The id of the row being edited. Empty when adding a new course.
  const [editingId, setEditingId] = useState(null);
  // Points to the form, so clicking Edit can scroll to it.
  const formRef = useRef(null);
  // The course waiting to be confirmed for removal. Empty when the box isn't showing.
  const [rowToRemove, setRowToRemove] = useState(null);
  // An error message to show. Empty when there's no error.
  const [error, setError] = useState("");
  // True while a request is being saved, to prevent double clicks.
  const [saving, setSaving] = useState(false);

  // Find the course selected in the form, if any.
  const selected = data.courses.find((course) => course.id === Number(form.course_id));
  // True when the selected course allows a range of credits.
  const variableCredits = selected && selected.min_credits !== selected.max_credits;
  // Students type the credits for manual courses and for courses with a range.
  const creditsEditable = form.is_manual || variableCredits;
  // Where the semester chosen in the form is today.
  const semester = semesterStatus(form.term, Number(form.year));
  // Coursework bars count toward the 45. The dissertation bar is shown separately.
  const courseworkBars = data.requirements.filter((item) => !item.name.startsWith("Dissertation"));
  // The separate CSI 898 bar.
  const dissertationBar = data.requirements.find((item) => item.name.startsWith("Dissertation"));

  // Updates one field in the form.
  function setField(name, value) {
    // Keep the other fields and replace this one.
    setForm((current) => ({ ...current, [name]: value }));
  }

  // Runs when the student picks a course from the dropdown.
  function selectCourse(courseId) {
    // Find the course they picked.
    const course = data.courses.find((item) => item.id === Number(courseId));
    // Save the choice, and fill in the course's credits.
    setForm((current) => ({ ...current, course_id: courseId, credits: course ? course.min_credits : "" }));
  }

  // Runs when the student switches between the course list and manual entry.
  function setManual(isManual) {
    // Clear the course fields, so values from the other mode aren't sent. The term, year and grade stay.
    setForm((current) => ({ ...current, is_manual: isManual, course_id: "", credits: "", manual_code: "", manual_title: "", manual_department: "", manual_is_research: false }));
  }

  // Clears the form and leaves edit mode.
  function resetForm() {
    // Empty the form.
    setForm(emptyForm());
    // Stop editing.
    setEditingId(null);
  }

  // Runs when the student clicks Edit on a course.
  function startEditing(row) {
    // Copy the course's values into the form.
    setForm({
      // A manual course has no listed course to select.
      course_id: row.is_manual ? "" : String(row.course_id), credits: row.credits, term: row.term, year: row.year, grade: row.grade ?? "",
      // Fill in the manual fields for a manual course, and leave them empty otherwise.
      is_manual: row.is_manual, manual_code: row.is_manual ? row.code : "", manual_title: row.is_manual ? row.title : "", manual_department: row.department ?? "", manual_is_research: row.is_research,
    });
    // Remember which row is being edited.
    setEditingId(row.id);
    // Scroll to the form, which may be out of view above the course list.
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    // Clear any old error.
    setError("");
  }

  // Sends a request and shows the updated data.
  async function send(path, options) {
    // Clear any old error.
    setError("");
    // Disable the buttons while this runs.
    setSaving(true);
    // Try the request.
    try {
      // Show the updated courses and progress from the backend.
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
    // The fields every course needs. The grade is only sent once the semester has ended, and an empty grade is sent as null.
    const shared = { credits: Number(form.credits), term: form.term, year: Number(form.year), grade: semester.ended ? form.grade || null : null };
    // Send the manual fields for a manual course, or the course's id for a listed one.
    const body = form.is_manual
      // The manual course's details.
      ? { ...shared, manual_code: form.manual_code, manual_title: form.manual_title, manual_department: form.manual_department, manual_is_research: form.manual_is_research }
      // The listed course's id.
      : { ...shared, course_id: Number(form.course_id) };
    // Edit the row if one is being edited, otherwise add a new one.
    const path = editingId ? `/students/me/courses/${editingId}` : "/students/me/courses";
    // Send the request, using PUT for an edit and POST for a new course.
    const saved = await send(path, { method: editingId ? "PUT" : "POST", body: JSON.stringify(body) });
    // Clear the form only if it saved.
    if (saved) resetForm();
  }

  // Runs when the student confirms the removal in the box.
  async function confirmRemove() {
    // Remember which course is being removed.
    const row = rowToRemove;
    // Close the box.
    setRowToRemove(null);
    // Delete the row.
    const removed = await send(`/students/me/courses/${row.id}`, { method: "DELETE" });
    // If the removed row was being edited, clear the form too.
    if (removed && editingId === row.id) resetForm();
  }

  // Draw the page.
  return (
    // Stack the page's sections with space between them.
    <div className="space-y-7">
      {/* The progress section. */}
      <section aria-labelledby="progress-heading" className="rounded-2xl border border-sage/25 bg-panel p-5 sm:p-6">
        {/* The heading on the left, and the overall total on the right. */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* The section's heading. */}
          <h2 id="progress-heading" className="font-display text-lg font-semibold text-white">Coursework progress</h2>
          {/* The overall total and percentage. */}
          <p className="text-sm text-mist/70"><span className="font-semibold text-sage">{data.coursework_credits}</span> of {data.coursework_required} credits ({data.percent}%)</p>
        </div>
        {/* One bar for each group that counts toward the 45. */}
        <div className="mt-5 space-y-4">
          {/* Draw each bar. */}
          {courseworkBars.map((item) => <ProgressBar key={item.name} name={item.name} earned={item.earned_credits} required={item.required_credits} />)}
        </div>
        {/* The CSI 790 deadline, in amber if it's overdue. */}
        <p className={`mt-4 text-sm ${data.csi_790_overdue ? "text-amber-200" : "text-mist/70"}`}>
          {/* Done, overdue, due by a semester, or no deadline if the student's details aren't recorded. */}
          CSI 790 Research Methods: {data.csi_790_complete ? "Complete" : data.csi_790_overdue ? `Overdue (was due by ${data.csi_790_deadline})` : data.csi_790_deadline ? `Due by ${data.csi_790_deadline}` : "Deadline not available"}
        </p>
        {/* CSI 898 is separated, because it doesn't count toward the 45. */}
        <div className="mt-5 border-t border-line pt-5">
          {/* Draw the CSI 898 bar. */}
          <ProgressBar name={dissertationBar.name} earned={dissertationBar.earned_credits} required={dissertationBar.required_credits} />
          {/* Explain why it's separate. */}
          <p className="mt-2 text-xs text-mist/50">These credits are separate from the {data.coursework_required} coursework credits. Together they make the 60-credit degree.</p>
        </div>
        {/* The grade averages. */}
        <div className="mt-5 flex flex-wrap gap-x-8 gap-y-2 border-t border-line pt-5 text-sm text-mist/70">
          {/* The average for core and breadth, which must be B+ or higher. */}
          <p>Core and breadth average: <strong className={data.core_breadth_average_met ? "text-sage" : "text-white"}>{data.core_breadth_average?.toFixed(2) ?? "Not available"}</strong> (needs 3.30)</p>
          {/* The GPA across all courses counting toward the degree. */}
          <p>Degree GPA: <strong className="text-white">{data.degree_gpa?.toFixed(2) ?? "Not available"}</strong></p>
        </div>
      </section>

      {/* The form for adding or editing a course. */}
      <form ref={formRef} onSubmit={handleSubmit} aria-labelledby="form-heading" className={`rounded-2xl border bg-panel p-5 sm:p-6 ${editingId ? "border-sage" : "border-line"}`}>
        {/* The heading changes when editing. */}
        <h2 id="form-heading" className="font-display text-lg font-semibold text-white">{editingId ? "Edit course" : "Add a course"}</h2>
        {/* The form's fields, in a responsive grid. */}
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {/* The switch to manual entry, across the full width. */}
          <label className="flex items-center gap-2 text-sm text-mist sm:col-span-2">
            {/* Ticking this replaces the course dropdown with the manual fields. */}
            <input type="checkbox" checked={form.is_manual} onChange={(event) => setManual(event.target.checked)} />
            {/* The checkbox's text. */}
            My UAlbany course isn't on the list
          </label>
          {/* Show the course dropdown, unless the course is being entered manually. */}
          {!form.is_manual && <CourseDropdown courses={data.courses} value={form.course_id} onSelect={selectCourse} />}
          {/* The course code, for a manual course. */}
          {form.is_manual && (
            // The field's label.
            <label className="text-sm text-mist">
              {/* The label's text. */}
              Course code
              {/* The code, with an example as a hint. */}
              <input type="text" required maxLength={20} placeholder="e.g. MAT 520" value={form.manual_code} onChange={(event) => setField("manual_code", event.target.value)} className={FIELD} />
            </label>
          )}
          {/* The department, for a manual course. */}
          {form.is_manual && (
            // The field's label.
            <label className="text-sm text-mist">
              {/* The label's text. */}
              Department
              {/* The student must choose one of these. */}
              <select required value={form.manual_department} onChange={(event) => setField("manual_department", event.target.value)} className={FIELD}>
                {/* The first option, shown before anything is picked. */}
                <option value="">Select a department</option>
                {/* A course from the CS department. */}
                <option value="cs">CS department</option>
                {/* A course from another department. */}
                <option value="non_cs">Non-CS department</option>
              </select>
            </label>
          )}
          {/* The course name, for a manual course, across the full width. */}
          {form.is_manual && (
            // The field's label.
            <label className="text-sm text-mist sm:col-span-2">
              {/* The label's text. */}
              Course name
              {/* The name of the course. */}
              <input type="text" required maxLength={255} value={form.manual_title} onChange={(event) => setField("manual_title", event.target.value)} className={FIELD} />
            </label>
          )}
          {/* The research flag, for a manual course, across the full width. */}
          {form.is_manual && (
            // The checkbox's label.
            <label className="flex items-center gap-2 text-sm text-mist sm:col-span-2">
              {/* Ticked courses count toward the 15-credit limit. */}
              <input type="checkbox" checked={form.manual_is_research} onChange={(event) => setField("manual_is_research", event.target.checked)} />
              {/* The checkbox's text. */}
              This is independent study or research (up to 15 credits can count)
            </label>
          )}
          {/* The bulletin's approval rule, shown for a non-CS course. */}
          {form.manual_department === "non_cs" && <p className="text-sm text-amber-200 sm:col-span-2">Non-CS courses must be chosen with your Research Advisor and approved by the CS Department. GradTrack doesn't record this approval.</p>}
          {/* The credits field. */}
          <label className="text-sm text-mist">
            {/* The label's text, with the allowed range for variable-credit courses. */}
            Credits{variableCredits ? ` (${selected.min_credits}–${selected.max_credits})` : ""}
            {/* Students can only type the credits when they can vary. A manual course allows 1 to 19. */}
            <input type="number" required value={form.credits} min={form.is_manual ? 1 : selected?.min_credits} max={form.is_manual ? 19 : selected?.max_credits} disabled={!creditsEditable} onChange={(event) => setField("credits", event.target.value)} className={`${FIELD} disabled:opacity-60`} />
          </label>
          {/* The grade dropdown. */}
          <label className="text-sm text-mist">
            {/* The label's text. */}
            Grade
            {/* The dropdown is locked to "In progress" until the semester has ended. */}
            <select value={semester.ended ? form.grade : ""} disabled={!semester.ended} onChange={(event) => setField("grade", event.target.value)} className={`${FIELD} disabled:opacity-60`}>
              {/* An empty grade means the course is still in progress. */}
              <option value="">In progress</option>
              {/* One option for each grade. */}
              {GRADES.map((grade) => <option key={grade} value={grade}>{grade}</option>)}
            </select>
            {/* Tell the student when they can enter a grade for a running semester. */}
            {semester.started && !semester.ended && <span className="mt-1 block text-xs text-mist/60">You can enter a grade starting {semester.endLabel}.</span>}
          </label>
          {/* The term dropdown. */}
          <label className="text-sm text-mist">
            {/* The label's text. */}
            Term
            {/* The dropdown itself. */}
            <select value={form.term} onChange={(event) => setField("term", event.target.value)} className={FIELD}>
              {/* The Spring option. */}
              <option value="spring">Spring</option>
              {/* The Fall option. */}
              <option value="fall">Fall</option>
            </select>
          </label>
          {/* The year field. */}
          <label className="text-sm text-mist">
            {/* The label's text. */}
            Year
            {/* The year, limited to the same range as the backend. */}
            <input type="number" required min={2000} max={2100} value={form.year} onChange={(event) => setField("year", event.target.value)} className={FIELD} />
          </label>
        </div>
        {/* Explain why a future semester can't be saved. */}
        {!semester.started && <p className="mt-4 text-sm text-amber-200">This semester hasn't started yet, so you can't add a course for it.</p>}
        {/* Any error, such as adding a duplicate course. */}
        {error && <p role="alert" className="mt-4 text-sm text-amber-200">{error}</p>}
        {/* The form's buttons. */}
        <div className="mt-5 flex gap-3">
          {/* Saves the course. */}
          <button type="submit" disabled={saving || !semester.started} className="rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:opacity-50">{saving ? "Saving…" : editingId ? "Save changes" : "Add course"}</button>
          {/* Cancel only appears while editing. */}
          {editingId && <button type="button" onClick={resetForm} className="rounded-lg border border-line px-4 py-2 text-sm text-mist hover:text-white">Cancel</button>}
        </div>
      </form>

      {/* The list of the student's courses. */}
      <section aria-labelledby="courses-heading">
        {/* The section's heading. */}
        <h2 id="courses-heading" className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">My courses ({data.my_courses.length})</h2>
        {/* A message if there are no courses yet. */}
        {data.my_courses.length === 0 && <p className="mt-3 rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">You haven't added any courses yet.</p>}
        {/* The list, with space between rows. */}
        <ul className="mt-3 space-y-2">
          {/* One row for each course. */}
          {data.my_courses.map((row) => (
            // The row's container.
            <li key={row.id} className={`flex flex-wrap items-center gap-3 rounded-xl border bg-panel px-4 py-3 text-sm ${editingId === row.id ? "border-sage" : "border-line"}`}>
              {/* The course's code and name, taking up the free space. */}
              <div className="min-w-0 flex-1 basis-56">
                {/* The course code. */}
                <p className="font-semibold text-white">{row.code}</p>
                {/* The course name. */}
                <p className="text-mist/70">{row.title}</p>
                {/* For a manual course, show that it was entered manually and its department. */}
                {row.is_manual && <p className="mt-1 text-xs text-mist/50">Entered manually · {row.department === "cs" ? "CS department" : "Non-CS department"}{row.is_research ? " · Independent study or research" : ""}</p>}
                {/* Why this course counts differently than the student might expect. */}
                {row.note && <p className="mt-2 text-xs text-amber-200">{row.note}</p>}
              </div>
              {/* The term, year and credits. */}
              <span className="text-mist/60">{row.term === "fall" ? "Fall" : "Spring"} {row.year} · {row.credits} cr</span>
              {/* The grade, or "In progress" if there isn't one. */}
              <span className="rounded-full border border-line px-3 py-1 text-xs text-mist">{row.grade ?? "In progress"}</span>
              {/* Loads this course into the form above. */}
              <button type="button" onClick={() => startEditing(row)} aria-pressed={editingId === row.id} className={`rounded-md px-2 py-1 text-sage underline underline-offset-4 transition-colors hover:bg-sage/15 hover:text-sage-light ${editingId === row.id ? "bg-sage/15 font-semibold" : ""}`}>{editingId === row.id ? "Editing" : "Edit"}</button>
              {/* Removes this course. */}
              <button type="button" disabled={saving} onClick={() => setRowToRemove(row)} className="rounded-md px-2 py-1 text-mist/70 underline underline-offset-4 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-50">Remove</button>
            </li>
          ))}
        </ul>
      </section>
      {/* The "are you sure?" box, while a removal is waiting to be confirmed. Completed coursework also gets a warning. */}
      {rowToRemove && <ConfirmDialog title={`Remove ${rowToRemove.code}?`} message={data.percent === 100 ? "If you no longer meet the coursework requirements, your Coursework milestone goes back to In progress." : undefined} confirmLabel="Remove" onConfirm={confirmRemove} onCancel={() => setRowToRemove(null)} />}
    </div>
  );
}

// The credit summary and button on the dashboard card, plus the popup they open.
export default function Coursework({ onChanged }) {
  // The data from the backend. Empty until it loads.
  const [data, setData] = useState(null);
  // An error message if the data couldn't load.
  const [loadError, setLoadError] = useState("");
  // True while the popup is open.
  const [open, setOpen] = useState(false);
  // Points to the popup element on the page.
  const dialogRef = useRef(null);
  // True if a course changed while the popup was open, so the dashboard knows to refresh.
  const changed = useRef(false);

  // Load the data once, so the card can show the credit summary.
  useEffect(() => {
    // Lets the request be cancelled if the dashboard closes.
    const controller = new AbortController();
    // Ask the backend for the course list and progress.
    api("/students/me/coursework", { signal: controller.signal })
      // Save the result, unless the request was cancelled.
      .then((result) => { if (!controller.signal.aborted) setData(result); })
      // Show any error, unless the request was cancelled.
      .catch((err) => { if (!controller.signal.aborted) setLoadError(err.message); });
    // Cancel the request if the dashboard closes.
    return () => controller.abort();
  // The empty list means this only runs once.
  }, []);

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

  // Stores updated data after a course is added, edited or removed.
  function handleUpdate(result) {
    // Show the new data.
    setData(result);
    // Remember that the dashboard needs to refresh.
    changed.current = true;
  }

  // Closes the popup, and refreshes the dashboard if anything changed.
  function close() {
    // Hide the popup.
    setOpen(false);
    // Only refresh if a course changed.
    if (changed.current) {
      // Reset the marker for next time.
      changed.current = false;
      // Ask the dashboard to reload its milestones and GPA.
      onChanged();
    }
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
    {/* The credit summary on the left, and the button on the right. */}
    <div className="flex flex-wrap items-center justify-between gap-4">
      {/* The load error, the credit summary, or a loading message. */}
      <p className={loadError ? "text-red-300" : "text-mist"}>{loadError || (data ? `${data.coursework_credits} of ${data.coursework_required} credits (${data.percent}%)` : "Loading your credits…")}</p>
      {/* Opens the popup, once the data has loaded. */}
      <button type="button" aria-haspopup="dialog" disabled={!data} onClick={() => setOpen(true)} className="cursor-pointer rounded-lg border border-sage/40 bg-sage/10 px-4 py-2 text-sm font-medium text-sage hover:bg-sage/20 disabled:cursor-not-allowed disabled:opacity-50">Manage coursework</button>
    </div>
    {/* The popup. Pressing Escape closes it through the same function as the buttons. */}
    <dialog ref={dialogRef} aria-labelledby="coursework-title" onKeyDown={handleKeyDown} onCancel={(event) => { event.preventDefault(); close(); }} className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-2xl border border-sage/30 bg-panel p-0 text-mist shadow-2xl backdrop:bg-black/75 backdrop:backdrop-blur-sm">
      {/* The popup's heading and close button. */}
      <header className="flex items-start justify-between gap-4 border-b border-line p-5 sm:p-6">
        {/* The title and explanation. */}
        <div>
          {/* The popup's title. */}
          <h2 id="coursework-title" className="font-display text-2xl font-bold text-white">Coursework</h2>
          {/* A short explanation. */}
          <p className="mt-2 text-sm text-mist/70">Select the courses you've taken and see how much of your coursework is complete.</p>
        </div>
        {/* The × button. */}
        <button type="button" onClick={close} aria-label="Close coursework" className="rounded-lg border border-line px-3 py-1 text-xl hover:border-sage">×</button>
      </header>
      {/* The content, which is rebuilt each time so the form starts empty. */}
      <div className="p-5 sm:p-6">{open && data && <CourseworkContent data={data} onUpdate={handleUpdate} />}</div>
      {/* The footer stays visible while the content scrolls. */}
      <footer className="sticky bottom-0 flex justify-end border-t border-line bg-panel p-5">
        {/* Closes the popup. */}
        <button type="button" onClick={close} className="rounded-lg bg-sage px-5 py-2 text-sm font-semibold text-ink hover:bg-sage-light">Close</button>
      </footer>
    </dialog>
  </>;
}
