// FacultyDashboard.jsx — THE FACULTY'S HOME PAGE. URL: /faculty
// Sprint 2: faculty overview with milestone review actions.

import { useEffect, useState } from "react";
import { api } from "../../api/client.js";

const STATUS_LABELS = {
  submitted: "Submitted",
  under_review: "Under review",
  revision_requested: "Revision requested",
};

function ProgressBar({ value }) {
  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
      className="h-2 overflow-hidden rounded-full bg-ink"
    >
      <div
        className="h-full rounded-full bg-sage"
        style={{ width: `${value}%` }}
      />
    </div>
  );
}

export default function FacultyDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [reviewing, setReviewing] = useState("");
  const [reviewError, setReviewError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    setError("");
    setData(null);

    api("/faculty/me/dashboard", {
      signal: controller.signal,
    })
      .then((result) => {
        if (!controller.signal.aborted) {
          setData(result);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(err.message);
        }
      });

    return () => controller.abort();
  }, [attempt]);

  async function handleReview(review, status) {
    const reviewKey = `${review.student_id}-${review.milestone_id}`;

    setReviewing(reviewKey);
    setReviewError("");

    try {
      await api(
        `/faculty/students/${review.student_id}/milestones/${review.milestone_id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status }),
        }
      );

      setAttempt((value) => value + 1);
    } catch (err) {
      setReviewError(err.message);
    } finally {
      setReviewing("");
    }
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-2xl border border-line bg-panel p-6"
      >
        <h1 className="font-display text-2xl font-bold text-white">
          Unable to load the faculty dashboard
        </h1>

        <p className="mt-3 text-mist/80">{error}</p>

        <button
          onClick={() => setAttempt((value) => value + 1)}
          className="mt-5 rounded-lg bg-sage px-4 py-2 font-semibold text-ink hover:bg-sage-light"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div
        role="status"
        className="rounded-2xl border border-line bg-panel p-8 text-mist/70"
      >
        Loading faculty dashboard…
      </div>
    );
  }

  const {
    faculty,
    summary,
    students,
    pending_reviews,
  } = data;

  return (
    <div className="space-y-7">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-sage">
          Faculty workspace
        </p>

        <h1 className="mt-2 font-display text-3xl font-bold text-white">
          Faculty Dashboard
        </h1>

        <p className="mt-2 text-sm text-mist/65">
          Welcome back, {faculty.full_name}.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-mist/55">
            Assigned students
          </p>

          <p className="mt-3 font-display text-3xl font-bold text-white">
            {summary.assigned_students}
          </p>

          <p className="mt-1 text-sm text-mist/60">
            Students currently assigned to you
          </p>
        </div>

        <div className="rounded-2xl border border-sage/25 bg-panel p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-mist/55">
            Pending reviews
          </p>

          <p className="mt-3 font-display text-3xl font-bold text-sage">
            {summary.pending_reviews}
          </p>

          <p className="mt-1 text-sm text-mist/60">
            Milestone submissions requiring attention
          </p>
        </div>
      </section>

      <section aria-labelledby="reviews-title">
        <div className="mb-3 flex items-center gap-2">
          <h2
            id="reviews-title"
            className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70"
          >
            Pending reviews
          </h2>

          <span className="rounded-full bg-panel px-2 py-0.5 text-xs text-mist/60">
            {pending_reviews.length}
          </span>
        </div>

        {reviewError && (
          <p
            role="alert"
            className="mb-3 rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200"
          >
            {reviewError}
          </p>
        )}

        {pending_reviews.length > 0 ? (
          <div className="space-y-2">
            {pending_reviews.map((review) => {
              const reviewKey =
                `${review.student_id}-${review.milestone_id}`;

              const isReviewing = reviewing === reviewKey;

              return (
                <div
                  key={reviewKey}
                  className="rounded-xl border border-line bg-panel p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="font-display font-semibold text-white">
                        {review.student_name}
                      </h3>

                      <p className="mt-1 text-sm text-mist/65">
                        {review.milestone_name}
                      </p>
                    </div>

                    <span className="rounded-full border border-sage/25 bg-sage/10 px-3 py-1 text-xs text-sage">
                      {STATUS_LABELS[review.status] || review.status}
                    </span>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={isReviewing}
                      onClick={() =>
                        handleReview(review, "approved")
                      }
                      className="rounded-lg bg-sage px-3 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Approve
                    </button>

                    <button
                      type="button"
                      disabled={isReviewing}
                      onClick={() =>
                        handleReview(
                          review,
                          "revision_requested"
                        )
                      }
                      className="rounded-lg border border-line px-3 py-2 text-sm font-semibold text-mist hover:border-sage/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Request revision
                    </button>

                    <button
                      type="button"
                      disabled={isReviewing}
                      onClick={() =>
                        handleReview(review, "rejected")
                      }
                      className="rounded-lg border border-red-400/30 px-3 py-2 text-sm font-semibold text-red-300 hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>

                  {isReviewing && (
                    <p className="mt-2 text-xs text-mist/50">
                      Updating milestone…
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">
            No milestone submissions are waiting for review.
          </p>
        )}
      </section>

      <section aria-labelledby="students-title">
        <div className="mb-3 flex items-center gap-2">
          <h2
            id="students-title"
            className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70"
          >
            My students
          </h2>

          <span className="rounded-full bg-panel px-2 py-0.5 text-xs text-mist/60">
            {students.length}
          </span>
        </div>

        {students.length > 0 ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {students.map((student) => (
              <article
                key={student.id}
                className="rounded-xl border border-line bg-panel p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-display font-semibold text-white">
                      {student.full_name}
                    </h3>

                    <p className="mt-1 text-xs text-mist/50">
                      {student.program_year > 0
                        ? `Program Year ${student.program_year}`
                        : student.program_year === 0
                        ? "Not yet started"
                        : "Program year unavailable"}
                    </p>
                  </div>

                  <span className="text-sm font-semibold text-sage">
                    {student.progress_percent}%
                  </span>
                </div>

                <div className="mt-4">
                  <ProgressBar value={student.progress_percent} />
                </div>

                <p className="mt-3 text-xs text-mist/55">
                  {student.completed_milestones} of{" "}
                  {student.total_milestones} milestones approved
                </p>
              </article>
            ))}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">
            No students are currently assigned to you.
          </p>
        )}
      </section>
    </div>
  );
}