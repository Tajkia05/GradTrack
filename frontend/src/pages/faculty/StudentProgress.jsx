import { useEffect, useState } from "react";
import {
  Link,
  useParams,
} from "react-router-dom";
import { api } from "../../api/client.js";


const STATUS_LABELS = {
  not_started: "Not started",
  in_progress: "In progress",
  submitted: "Submitted",
  under_review: "Under review",
  revision_requested: "Revision requested",
  approved: "Approved",
  rejected: "Rejected",
};


function ProgressBar({ value }) {
  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
      className="h-3 overflow-hidden rounded-full bg-ink"
    >
      <div
        className="h-full rounded-full bg-sage"
        style={{ width: `${value}%` }}
      />
    </div>
  );
}


function statusClass(status) {
  if (status === "approved") {
    return "border-sage/30 bg-sage/10 text-sage";
  }

  if (
    status === "submitted" ||
    status === "under_review"
  ) {
    return "border-blue-400/30 bg-blue-400/10 text-blue-200";
  }

  if (status === "revision_requested") {
    return "border-amber-400/30 bg-amber-400/10 text-amber-200";
  }

  if (status === "rejected") {
    return "border-red-400/30 bg-red-400/10 text-red-200";
  }

  return "border-line bg-ink/20 text-mist/65";
}


export default function StudentProgress() {
  const { studentId } = useParams();

  const [data, setData] = useState(null);
  const [error, setError] = useState("");


  useEffect(() => {
    const controller = new AbortController();

    setData(null);
    setError("");

    api(
      `/faculty/students/${studentId}/progress`,
      {
        signal: controller.signal,
      }
    )
      .then((progress) => {
        if (!controller.signal.aborted) {
          setData(progress);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(err.message);
        }
      });

    return () => controller.abort();
  }, [studentId]);


  if (error) {
    return (
      <div className="rounded-2xl border border-line bg-panel p-6">
        <h1 className="font-display text-2xl font-bold text-white">
          Unable to load student progress
        </h1>

        <p
          role="alert"
          className="mt-3 text-sm text-red-300"
        >
          {error}
        </p>

        <Link
          to="/faculty"
          className="mt-5 inline-block text-sm font-semibold text-sage hover:text-sage-light"
        >
          ← Back to Faculty Dashboard
        </Link>
      </div>
    );
  }


  if (!data) {
    return (
      <div
        role="status"
        className="rounded-2xl border border-line bg-panel p-8 text-mist/70"
      >
        Loading student progress…
      </div>
    );
  }


  return (
    <div className="space-y-7">
      <div>
        <Link
          to="/faculty"
          className="text-sm font-semibold text-sage hover:text-sage-light"
        >
          ← Back to Faculty Dashboard
        </Link>
      </div>

      <header>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-sage">
          Advisee progress
        </p>

        <h1 className="mt-2 font-display text-3xl font-bold text-white">
          {data.student_name}
        </h1>

        <p className="mt-2 text-sm text-mist/65">
          {data.email}
          {" · "}
          {data.program_year > 0
            ? `Program Year ${data.program_year}`
            : data.program_year === 0
            ? "Not yet started"
            : "Program year unavailable"}
        </p>
      </header>

      <section className="rounded-2xl border border-line bg-panel p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/55">
              Overall progress
            </p>

            <p className="mt-2 font-display text-4xl font-bold text-sage">
              {data.progress_percent}%
            </p>
          </div>

          <p className="text-sm text-mist/65">
            {data.completed_milestones} of{" "}
            {data.total_milestones} milestones
            approved
          </p>
        </div>

        <div className="mt-5">
          <ProgressBar
            value={data.progress_percent}
          />
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <SummaryCard
          label="Completed"
          value={data.completed_milestones}
        />

        <SummaryCard
          label="Remaining"
          value={data.remaining_milestones}
        />

        <SummaryCard
          label="Total milestones"
          value={data.total_milestones}
        />
      </section>

      <section>
        <div className="mb-3">
          <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">
            Milestone details
          </h2>

          <p className="mt-1 text-sm text-mist/50">
            Completed work, current work, and
            milestones still remaining.
          </p>
        </div>

        {data.milestones.length > 0 ? (
          <div className="space-y-3">
            {data.milestones.map(
              (milestone, index) => (
                <article
                  key={milestone.milestone_id}
                  className="rounded-xl border border-line bg-panel p-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex gap-4">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-line bg-ink/30 text-sm font-semibold text-mist">
                        {index + 1}
                      </div>

                      <div>
                        <h3 className="font-display font-semibold text-white">
                          {
                            milestone.milestone_name
                          }
                        </h3>

                        {milestone.completed_on && (
                          <p className="mt-1 text-xs text-mist/50">
                            Completed on{" "}
                            {
                              milestone.completed_on
                            }
                          </p>
                        )}
                      </div>
                    </div>

                    <span
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${statusClass(
                        milestone.status
                      )}`}
                    >
                      {STATUS_LABELS[
                        milestone.status
                      ] || milestone.status}
                    </span>
                  </div>
                </article>
              )
            )}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">
            No milestones are configured.
          </p>
        )}
      </section>
    </div>
  );
}


function SummaryCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-5">
      <p className="text-xs uppercase tracking-[0.14em] text-mist/55">
        {label}
      </p>

      <p className="mt-3 font-display text-3xl font-bold text-white">
        {value}
      </p>
    </div>
  );
}
