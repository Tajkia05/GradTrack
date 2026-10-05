// Student progress comes from the API; prerequisites and deadlines are calculated there.
import { useEffect, useState } from "react";
import { api } from "../../api/client.js";

const STATUS_LABELS = {
  not_started: "Not started", in_progress: "In progress", submitted: "Submitted",
  under_review: "In review", revision_requested: "Revision requested",
  approved: "Approved", rejected: "Rejected",
};
const SECTIONS = [
  { key: "current", title: "Current", description: "The milestones you’re working on now." },
  { key: "blocked", title: "Blocked", description: "Complete these prerequisites to move forward." },
  { key: "upcoming", title: "Upcoming", description: "Ready when you are — your next steps." },
  { key: "completed", title: "Completed" },
];

function formatDate(value) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

function MilestoneCard({ milestone }) {
  const completed = milestone.category === "completed";
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
            {completed ? (milestone.completed_on ? formatDate(milestone.completed_on) : "Approval date unavailable")
              : milestone.deadline_label ? `Due ${milestone.deadline_label}` : "No scheduled deadline"}
          </span>
          {milestone.overdue && <span className="font-medium text-amber-200">Overdue</span>}
          <span className={`rounded-full border px-3 py-1 text-xs ${completed ? "border-sage/25 bg-sage/10 text-sage" : "border-line text-mist"}`}>
            {STATUS_LABELS[milestone.status] || milestone.status}
          </span>
          <span aria-hidden="true" className="text-mist/50 transition-transform group-open:rotate-180">⌄</span>
        </div>
      </summary>
      <div className="space-y-3 border-t border-line px-5 py-4 text-sm text-mist/80">
        <p>{completed ? "This milestone has been approved." : milestone.eligible ? "Prerequisites are met. This milestone is available to work on." : "This milestone is waiting on the requirements below."}</p>
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

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    setData(null);
    api("/students/me/milestones", { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setData(result); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [attempt]);

  if (error) return (
    <div role="alert" className="rounded-2xl border border-line bg-panel p-6">
      <h1 className="font-display text-2xl font-bold text-white">Unable to load your progress</h1>
      <p className="mt-3 text-mist/80">{error}</p>
      <button onClick={() => setAttempt((value) => value + 1)} className="mt-5 rounded-lg bg-sage px-4 py-2 font-semibold text-ink hover:bg-sage-light">Try again</button>
    </div>
  );
  if (!data) return <div role="status" className="rounded-2xl border border-line bg-panel p-8 text-mist/70">Loading your progress…</div>;

  const { student, summary, milestones } = data;
  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-sage">Your degree, one step at a time</p>
          <h1 className="mt-2 font-display text-3xl font-bold text-white">My progress</h1>
          <p className="mt-2 text-sm text-mist/65">Welcome back, {student.full_name}.</p>
        </div>
        <span className="rounded-full border border-line px-3 py-1.5 text-xs text-mist/70">
          {student.enrollment_status === "part_time" ? "Part-time" : student.enrollment_status === "full_time" ? "Full-time" : "Enrollment not set"}
          {student.advanced_standing && " · Advanced standing"}
        </span>
      </header>

      <section aria-labelledby="progress-title" className="rounded-2xl border border-sage/25 bg-panel p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="progress-title" className="font-display text-lg font-semibold text-white">Program progress{student.program_year > 0 ? ` — Year ${student.program_year}` : student.program_year === 0 ? " — Not yet started" : ""}</h2>
          <p className="text-sm text-mist/70"><span className="font-semibold text-sage">{summary.completed}</span> of {summary.total} milestones</p>
        </div>
        <div role="progressbar" aria-label="Approved milestones" aria-valuenow={summary.percent} aria-valuemin={0} aria-valuemax={100} aria-valuetext={`${summary.completed} of ${summary.total} milestones approved`} className="my-5 h-3 overflow-hidden rounded-full bg-ink">
          <div className="h-full rounded-full bg-sage" style={{ width: `${summary.percent}%` }} />
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-mist/65">
          {["completed", "current", "upcoming", "blocked"].map((key) => <span key={key}><strong className={key === "completed" ? "text-sage" : "text-white"}>{summary[key]}</strong> {key}</span>)}
        </div>
        <p className="mt-4 text-xs leading-relaxed text-mist/50">{student.enrollment_status === "part_time" ? "Part-time deadlines are doubled; defense is capped at 8 years. " : ""}Deadlines are shown by academic semester.</p>
      </section>

      {student.advisor_id === null && (
        <aside className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-dashed border-sage/40 bg-sage/5 p-5">
          <div>
            <h2 className="font-display font-semibold text-white">Declare your advisor</h2>
            <p className="mt-1 text-sm text-mist/70">An advisor is required before your comprehensive exam.</p>
            <p id="advisor-help" className="mt-2 text-xs text-mist/50">Advisor selection will be available in a future update.</p>
          </div>
          <button disabled aria-describedby="advisor-help" className="cursor-not-allowed rounded-lg border border-line px-4 py-2 text-sm text-mist/45">Choose advisor</button>
        </aside>
      )}

      {summary.total === 0 ? <p className="rounded-xl border border-line p-6 text-mist/70">No program milestones have been configured yet.</p> : SECTIONS.map(({ key, title, description }) => {
        const items = milestones.filter((milestone) => milestone.category === key);
        const visible = key === "completed" && !showAllCompleted ? items.slice(0, 1) : items;
        return (
          <section key={key} aria-labelledby={`${key}-title`}>
            <div className="mb-3 flex items-center gap-2">
              <h2 id={`${key}-title`} className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">{title}</h2>
              <span className="rounded-full bg-panel px-2 py-0.5 text-xs text-mist/60">{items.length}</span>
            </div>
            {items.length > 0 ? <div className="space-y-2">{visible.map((milestone) => <MilestoneCard key={milestone.id} milestone={milestone} />)}</div>
              : <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">{key === "completed" ? "Your first approval will appear here." : `No ${title.toLowerCase()} milestones.`}</p>}
            {key === "completed" && items.length > 1 && <button aria-expanded={showAllCompleted} onClick={() => setShowAllCompleted((value) => !value)} className="mt-3 text-sm text-sage underline underline-offset-4 hover:text-sage-light">{showAllCompleted ? "Show less" : `Show ${items.length - 1} more`}</button>}
            {items.length > 0 && key !== "completed" && <p className="mt-2 text-xs text-mist/45">{description} Select a milestone to see details.</p>}
          </section>
        );
      })}

      <footer className="border-t border-line pt-6">
        <div className={`grid gap-3 ${student.advanced_standing ? "sm:grid-cols-2" : ""}`}>
          <div className="rounded-xl border border-line bg-panel p-4">
            <h2 className="font-display font-semibold text-mist">Committee</h2>
            <p className="mt-1 text-xs text-mist/50">Committee management is coming soon.</p>
          </div>
          {student.advanced_standing && <div className="rounded-xl border border-line bg-panel p-4">
            <h2 className="font-display font-semibold text-mist">Transfer credit</h2>
            <p className="mt-1 text-xs text-mist/50">Transfer credit requests are coming soon.</p>
          </div>}
        </div>
        <p className="mt-4 text-xs text-mist/45">Progress as of {formatDate(data.as_of)}{student.advisor_name ? ` · Advisor: ${student.advisor_name}` : ""}</p>
      </footer>
    </div>
  );
}
