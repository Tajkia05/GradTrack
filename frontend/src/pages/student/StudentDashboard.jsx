// Student progress comes from the API; prerequisites and deadlines are calculated there.
import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client.js";
import AdvisorDeclaration from "./AdvisorDeclaration.jsx";
import AdvisorDeclarationDetails from "./AdvisorDeclarationDetails.jsx";
// The credit summary, button and popup on the Coursework card.
import Coursework from "./Coursework.jsx";
// The summary, button and popup on the Committee formation card.
import Committee from "./Committee.jsx";
// The button and popup for submitting a milestone's documents.
import MilestoneSubmission from "./MilestoneSubmission.jsx";

// The milestones that are submitted with documents and reviewed by the advisor.
const SUBMITTABLE_MILESTONES = ["comprehensive exam", "dissertation proposal", "dissertation defense"];

const STATUS_LABELS = {
  not_started: "Not started", in_progress: "In progress", submitted: "Submitted",
  under_review: "In review", revision_requested: "Revision requested",
  approved: "Approved", rejected: "Rejected",
};

const SECTIONS = [
  { key: "current", title: "Ongoing", description: "The milestones you’re working on now." },
  { key: "blocked", title: "Blocked", description: "Complete these prerequisites to move forward." },
  { key: "upcoming", title: "Available", description: "Ready when you are — your next steps." },
  { key: "completed", title: "Completed" },
];

function formatDate(value) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

// onProgressChanged reloads the dashboard after a student changes their courses or committee.
// Shows an exact date and time, e.g. "Nov 2, 2026, 3:30 PM".
function formatDateTime(value) {
  // Use the viewer's own time zone.
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function MilestoneCard({ milestone, onProgressChanged }) {
  const completed = milestone.category === "completed";
  const isAdvisorDeclaration = completed && milestone.name.toLowerCase() === "advisor declaration";
  // "Completed" for milestones the app finishes by itself, and "Approved" when a person decides.
  const finishedWord = milestone.is_automatic ? "Completed" : "Approved";
  return (
    <details className="group rounded-xl border border-line bg-panel open:border-sage/40">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-3 rounded-xl p-4 focus-visible:outline-2 focus-visible:outline-sage sm:p-5 [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true" className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm ${completed ? "border-sage/30 bg-sage/10 text-sage" : milestone.category === "blocked" ? "border-amber-300/25 text-amber-200" : "border-line text-mist/60"}`}>
          {completed ? "✓" : milestone.category === "blocked" ? "!" : "○"}
        </span>
        <div className="min-w-0 flex-1 basis-40">
          <h3 className={`font-display font-semibold ${completed ? "text-mist" : "text-white"}`}>{milestone.name}</h3>
          {milestone.blocked_reasons.length > 0 && (
            <p className="mt-1 text-sm leading-relaxed text-amber-200/80">{milestone.blocked_reasons.join(" ")}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm">
          <span className="text-mist/60">
            {/* A finished milestone shows its exact time when recorded, and otherwise only its date. */}
            {completed ? (milestone.approved_at ? `${finishedWord} ${formatDateTime(milestone.approved_at)}` : milestone.completed_on ? `${finishedWord} ${formatDate(milestone.completed_on)}` : "Date unavailable")
              : milestone.deadline_label ? `Due ${milestone.deadline_label}` : "No scheduled deadline"}
          </span>
          {milestone.overdue && <span className="font-medium text-amber-200">Overdue</span>}
          <span className={`rounded-full border px-3 py-1 text-xs ${completed ? "border-sage/25 bg-sage/10 text-sage" : "border-line text-mist"}`}>
            {completed ? finishedWord : STATUS_LABELS[milestone.status] || milestone.status}
          </span>
          <span aria-hidden="true" className="text-mist/50 transition-transform group-open:rotate-180">⌄</span>
        </div>
      </summary>
      <div className="space-y-3 border-t border-line px-5 py-4 text-sm text-mist/80">
        {isAdvisorDeclaration ? (
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-mist/60">Declaration date</p>
              <p className="mt-1 font-display text-lg font-semibold text-white">{milestone.completed_on
                ? <time dateTime={milestone.completed_on}>{new Intl.DateTimeFormat("en-US", { dateStyle: "long" }).format(new Date(`${milestone.completed_on}T12:00:00`))}</time>
                : "Date not recorded"}</p>
              <p className="mt-2">Declaration completed. No faculty approval was required.</p>
            </div>
            <AdvisorDeclarationDetails />
          </div>
        ) : <p>{completed ? `This milestone has been ${finishedWord.toLowerCase()}.` : milestone.eligible ? "Prerequisites are met. This milestone is available to work on." : "This milestone is waiting on the requirements below."}</p>}
        {/* Only the Coursework card gets the credit summary and button. */}
        {milestone.name.toLowerCase() === "coursework" && <Coursework onChanged={onProgressChanged} />}
        {/* Only the Committee formation card gets the committee summary and button. */}
        {milestone.name.toLowerCase() === "committee formation" && <Committee onChanged={onProgressChanged} />}
        {/* These milestones get the submission button. */}
        {SUBMITTABLE_MILESTONES.includes(milestone.name.toLowerCase()) && <MilestoneSubmission milestoneId={milestone.id} milestoneName={milestone.name} onChanged={onProgressChanged} />}
        {milestone.requirements.length > 0 && <ul className="space-y-2">
          {milestone.requirements.map((requirement) => (
            <li key={requirement.name} className="flex gap-2">
              <span className={requirement.met ? "text-sage" : "text-amber-200"}>{requirement.met ? "✓" : "•"}</span>
              <span>{requirement.explanation}</span>
            </li>
          ))}
        </ul>}
        {milestone.deadline_semester !== null && <p className="text-mist/60">Program deadline: semester {milestone.deadline_semester}{milestone.deadline_label ? ` (${milestone.deadline_label})` : ". Start term is needed to calculate the calendar deadline"}.</p>}
      </div>
    </details>
  );
}

export default function StudentDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [showAllCompleted, setShowAllCompleted] = useState(false);
  const [activeSection, setActiveSection] = useState("all");
  const [declarationMessage, setDeclarationMessage] = useState("");
  const declarationNotice = useRef(null);

  useEffect(() => {
    if (declarationMessage) declarationNotice.current?.focus();
  }, [declarationMessage]);

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    setData(null);
    api("/students/me/milestones", { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setData(result); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [attempt]);

  // Reloads the milestones and GPA without showing the loading message.
  function refreshDashboard() {
    // Ask the backend for the latest dashboard.
    api("/students/me/milestones")
      // Show the new data.
      .then(setData)
      // Show any error.
      .catch((err) => setError(err.message));
  }

  if (error) return (
    <div role="alert" className="rounded-2xl border border-line bg-panel p-6">
      <h1 className="font-display text-2xl font-bold text-white">Unable to load your progress</h1>
      <p className="mt-3 text-mist/80">{error}</p>
      <button onClick={() => setAttempt((value) => value + 1)} className="mt-5 rounded-lg bg-sage px-4 py-2 font-semibold text-ink hover:bg-sage-light">Try again</button>
    </div>
  );
  if (!data) return <div role="status" className="rounded-2xl border border-line bg-panel p-8 text-mist/70">Loading your progress…</div>;

  const { student, summary, milestones } = data;

  const visibleSections =
    activeSection === "all"
      ? SECTIONS
      : SECTIONS.filter((section) => section.key === activeSection);

  return (
    <div className="space-y-7">
      {/* The greeting, with the student's key details in one small row underneath. */}
      <header>
        {/* The page's main heading. */}
        <h1 className="font-display text-3xl font-bold text-white">Welcome back, {student.full_name}</h1>
        {/* The details row, which wraps on narrow screens. */}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          {/* The advisor, only once one is declared. */}
          {student.advisor_name && <span className="rounded-full border border-sage/25 bg-sage/5 px-3 py-1 text-mist">Advisor: <span className="font-medium text-white">{student.advisor_name}</span></span>}
          {/* Full-time or part-time. */}
          <span className="rounded-full border border-line px-3 py-1 text-mist/70">{student.enrollment_status === "part_time" ? "Part-time" : student.enrollment_status === "full_time" ? "Full-time" : "Enrollment not set"}</span>
          {/* Advanced standing, only for students who have it. */}
          {student.advanced_standing && <span className="rounded-full border border-line px-3 py-1 text-mist/70">Advanced standing</span>}
        </div>
      </header>

      <section aria-labelledby="progress-title" className="rounded-2xl border border-sage/25 bg-panel p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="progress-title" className="font-display text-lg font-semibold text-white">Program progress{student.program_year > 0 ? ` — Year ${student.program_year}` : student.program_year === 0 ? " — Not yet started" : ""}</h2>
          <p className="text-sm text-mist/70"><span className="font-semibold text-sage">{summary.completed}</span> of {summary.total} milestones</p>
        </div>
        <p className="mt-3 text-base font-medium text-mist">
          Progress as of <time dateTime={data.as_of} className="font-semibold text-sage">{formatDate(data.as_of)}</time>
        </p>
        <div role="progressbar" aria-label="Finished milestones" aria-valuenow={summary.percent} aria-valuemin={0} aria-valuemax={100} aria-valuetext={`${summary.completed} of ${summary.total} milestones finished`} className="my-5 h-3 overflow-hidden rounded-full bg-ink">
          <div className="h-full rounded-full bg-sage" style={{ width: `${summary.percent}%` }} />
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-mist/65">
          {["completed", "current", "upcoming", "blocked"].map((key) => <span key={key}><strong className={key === "completed" ? "text-sage" : "text-white"}>{summary[key]}</strong> {key === "upcoming" ? "available" : key === "current" ? "ongoing" : key}</span>)}
        </div>
        <p className="mt-4 text-xs leading-relaxed text-mist/50">{student.enrollment_status === "part_time" ? "Part-time deadlines are doubled; defense is capped at 8 years. " : ""}Deadlines are shown by academic semester.</p>
      </section>

      <nav aria-label="Filter milestones by status" className="flex flex-wrap gap-2">
        {["all", "current", "blocked", "upcoming", "completed"].map((key) => {
          const count = key === "all" ? summary.total : summary[key];
          const selected = activeSection === key;

          return (
            <button
              key={key}
              type="button"
              aria-pressed={selected}
              onClick={() => setActiveSection(key)}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                selected
                  ? "border-sage bg-sage/15 text-sage"
                  : "border-line text-mist/65 hover:border-sage/40 hover:text-white"
              }`}
            >
              {/* Students see "Ongoing" and "Available", which the API calls "current" and "upcoming". */}
              {key === "all" ? "All" : key === "upcoming" ? "Available" : key === "current" ? "Ongoing" : key.charAt(0).toUpperCase() + key.slice(1)}
              <span className="ml-2 text-xs opacity-70">{count}</span>
            </button>
          );
        })}
      </nav>

      {declarationMessage && <p ref={declarationNotice} tabIndex={-1} role="status" className="rounded-xl border border-sage/30 bg-sage/10 p-4 text-sage focus:outline-none">{declarationMessage}</p>}
      {student.advisor_id === null && <AdvisorDeclaration onDeclared={(dashboard) => {
        setData(dashboard);
        setActiveSection("all");
        setDeclarationMessage(`${dashboard.student.advisor_name} is now your research advisor. Your progress has been updated.`);
      }} />}

      {summary.total === 0 ? <p className="rounded-xl border border-line p-6 text-mist/70">No program milestones have been configured yet.</p> : visibleSections.map(({ key, title, description }) => {
        const items = milestones.filter((milestone) => milestone.category === key);
        const visible = key === "completed" && !showAllCompleted && activeSection === "all" ? items.slice(0, 1) : items;
        return (
          <section key={key} aria-labelledby={`${key}-title`}>
            <div className="mb-3 flex items-center gap-2">
              <h2 id={`${key}-title`} className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">{title}</h2>
              <span className="rounded-full bg-panel px-2 py-0.5 text-xs text-mist/60">{items.length}</span>
            </div>
            {items.length > 0 ? <div className="space-y-2">{visible.map((milestone) => <MilestoneCard key={milestone.id} milestone={milestone} onProgressChanged={refreshDashboard} />)}</div>
              : <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">{key === "completed" ? "Your first finished milestone will appear here." : `No ${title.toLowerCase()} milestones.`}</p>}
            {key === "completed" && activeSection === "all" && items.length > 1 && <button aria-expanded={showAllCompleted} onClick={() => setShowAllCompleted((value) => !value)} className="mt-3 text-sm text-sage underline underline-offset-4 hover:text-sage-light">{showAllCompleted ? "Show less" : `Show ${items.length - 1} more`}</button>}
            {items.length > 0 && key !== "completed" && <p className="mt-2 text-xs text-mist/45">{description} Select a milestone to see details.</p>}
          </section>
        );
      })}

      {/* The footer only has the transfer credit card, so it only shows for students with advanced standing. */}
      {student.advanced_standing && <footer className="border-t border-line pt-6">
        <div className="rounded-xl border border-line bg-panel p-4">
          <h2 className="font-display font-semibold text-mist">Transfer credit</h2>
          <p className="mt-1 text-xs text-mist/50">Transfer credit requests are coming soon.</p>
        </div>
      </footer>}
    </div>
  );
}
