// FacultyDashboard.jsx — THE FACULTY'S HOME PAGE. URL: /faculty
// Sprint 2: faculty overview with milestone reviews, committee management,
// and detailed advisee progress.

import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, getToken } from "../../api/client.js";
import ConfirmDialog from "../../components/ConfirmDialog.jsx";
import { useToast } from "../../components/Toast.jsx";


const STATUS_LABELS = {
  submitted: "Submitted",
  under_review: "Under review",
  revision_requested: "Revision requested",
};

// Shows a presentation date, e.g. "Wed, Nov 11, 2026, 9:00 AM".
function formatPresentationDate(value) {
  // Use the viewer's own time zone.
  return new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

// For each presentation stage: its badge, the badge's colors, and what it means for the viewer.
// isAdvisor is true for the student's advisor, who records the decision, and false for other committee members.
const PRESENTATION_STAGES = {
  // The document is approved, and the student hasn't proposed dates yet.
  waiting_for_dates: { badge: "Waiting for dates", tone: "border-line text-mist", next: (item) => `Document approved. Waiting for ${item.student_name} to propose presentation dates.` },
  // The student proposed dates, and the committee is answering.
  awaiting_availability: { badge: "Dates proposed", tone: "border-amber-300/40 text-amber-200", next: (item) => `${item.student_name} proposed ${item.option_count} date${item.option_count === 1 ? "" : "s"}. Once everyone on the committee can attend one, ${item.student_name} chooses it.` },
  // The advisor asked for new dates.
  needs_new_dates: { badge: "New dates needed", tone: "border-amber-300/40 text-amber-200", next: (item) => `Waiting for ${item.student_name} to propose new dates.` },
  // The date is chosen and still ahead.
  scheduled: { badge: "Upcoming", tone: "border-sage/40 text-sage", next: (item, isAdvisor) => isAdvisor ? "Attend the presentation. Your final decision opens after it." : "Attend the presentation. The advisor records the committee's final decision after it." },
  // The date has passed.
  held: { badge: "✓ Presentation done", tone: "border-sage bg-sage/15 text-sage", next: (item, isAdvisor) => isAdvisor ? "The presentation has taken place. Record your final decision in Pending reviews." : "The presentation has taken place. The advisor records the committee's final decision." },
  // A revision was requested after the presentation.
  revision_requested: { badge: "✓ Presentation done", tone: "border-sage bg-sage/15 text-sage", next: (item, isAdvisor) => `${isAdvisor ? "You" : "The advisor"} requested a revision. Waiting for ${item.student_name}'s revised document.` },
};

// How each review decision is worded in the success message.
const DECISION_LABELS = {
  approved: "approved",
  rejected: "rejected",
  revision_requested: "sent back for revision",
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
  const showToast = useToast();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  const [reviewing, setReviewing] = useState("");
  const [reviewError, setReviewError] = useState("");
  const [reviewComments, setReviewComments] = useState({});
  const [submissions, setSubmissions] = useState({});
  const [submissionErrors, setSubmissionErrors] = useState({});

  const [invitations, setInvitations] = useState([]);
  const [invitationError, setInvitationError] = useState("");
  const [respondingToInvitation, setRespondingToInvitation] =
    useState(null);

  const [memberships, setMemberships] = useState([]);
  const [membershipError, setMembershipError] = useState("");
  const [leavingMembership, setLeavingMembership] =
    useState(null);

  // The committee waiting to be confirmed for leaving.
  const [membershipToLeave, setMembershipToLeave] =
    useState(null);

  // The address bar, which holds the item a notification opened.
  const location = useLocation();

  // The last notification click that has been handled.
  const handledClick = useRef(null);

  // The review or section to highlight for a moment.
  const [highlightedId, setHighlightedId] =
    useState(null);


  // When a notification opens this page, scroll to its item
  // and highlight it.
  useEffect(() => {
    if (
      !data ||
      handledClick.current === location.key
    ) {
      return;
    }

    const params = new URLSearchParams(
      location.search
    );

    const student = params.get("student");
    const milestone = params.get("milestone");
    const section = params.get("section");

    if (!section && !student) {
      return;
    }

    handledClick.current = location.key;

    const reviewId = student
      ? `review-${student}-${milestone}`
      : null;

    const targetId =
      reviewId &&
      document.getElementById(reviewId)
        ? reviewId
        : `section-${section || "reviews"}`;

    document
      .getElementById(targetId)
      ?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });

    setHighlightedId(targetId);

    const timer = setTimeout(
      () => setHighlightedId(null),
      3000
    );

    return () => clearTimeout(timer);
  }, [
    data,
    location.key,
    location.search,
  ]);


  const highlightClass = (id) =>
    highlightedId === id
      ? "rounded-xl ring-2 ring-sage"
      : "";


  // Load the faculty dashboard, committee invitations,
  // and committee memberships together.
  useEffect(() => {
    const controller = new AbortController();

    setError("");
    setInvitationError("");
    setMembershipError("");
    setData(null);

    Promise.all([
      api("/faculty/me/dashboard", {
        signal: controller.signal,
      }),
      api(
        "/faculty/me/committee-invitations",
        {
          signal: controller.signal,
        }
      ),
      api(
        "/faculty/me/committee-memberships",
        {
          signal: controller.signal,
        }
      ),
    ])
      .then(
        ([
          dashboard,
          committeeInvitations,
          committeeMemberships,
        ]) => {
          if (!controller.signal.aborted) {
            setData(dashboard);
            setInvitations(
              committeeInvitations
            );
            setMemberships(
              committeeMemberships
            );
          }
        }
      )
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(err.message);
        }
      });

    return () => controller.abort();
  }, [attempt]);


  // Load submission attempts and files for every pending review.
  useEffect(() => {
    if (!data?.pending_reviews) {
      return;
    }

    const controller = new AbortController();

    async function loadSubmissions() {
      const loadedSubmissions = {};
      const loadedErrors = {};

      await Promise.all(
        data.pending_reviews.map(
          async (review) => {
            const reviewKey =
              `${review.student_id}-${review.milestone_id}`;

            try {
              const attempts = await api(
                `/faculty/students/${review.student_id}/milestones/${review.milestone_id}/submissions`,
                {
                  signal:
                    controller.signal,
                }
              );

              loadedSubmissions[
                reviewKey
              ] = attempts;
            } catch (err) {
              if (
                !controller.signal.aborted
              ) {
                loadedErrors[
                  reviewKey
                ] = err.message;
              }
            }
          }
        )
      );

      if (!controller.signal.aborted) {
        setSubmissions(
          loadedSubmissions
        );
        setSubmissionErrors(
          loadedErrors
        );
      }
    }

    loadSubmissions();

    return () => controller.abort();
  }, [data]);


  async function handleReview(
    review,
    status
  ) {
    const reviewKey =
      `${review.student_id}-${review.milestone_id}`;

    const comment =
      reviewComments[
        reviewKey
      ]?.trim() || null;

    setReviewing(reviewKey);
    setReviewError("");

    try {
      // The backend says whether Approve completed the milestone or only approved the document.
      const result = await api(
        `/faculty/students/${review.student_id}/milestones/${review.milestone_id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            status,
            comment,
          }),
        }
      );

      setReviewComments(
        (current) => {
          const updated = {
            ...current,
          };

          delete updated[reviewKey];

          return updated;
        }
      );

      setAttempt(
        (value) => value + 1
      );

      // Before the presentation, Approve only approves the document, so say so.
      showToast(
        status === "approved" && result.status === "under_review"
          ? `${review.student_name}'s ${review.milestone_name} document was approved. The final decision comes after the presentation.`
          : `${review.student_name}'s ${review.milestone_name} was ${DECISION_LABELS[status]}.`
      );
    } catch (err) {
      setReviewError(err.message);
    } finally {
      setReviewing("");
    }
  }


  async function handleDocumentDownload(
    document
  ) {
    setReviewError("");

    try {
      const token = getToken();

      const response = await fetch(
        `/api/milestone-documents/${document.id}`,
        {
          headers: {
            ...(token && {
              Authorization:
                `Bearer ${token}`,
            }),
          },
        }
      );

      if (
        response.status === 401 &&
        token
      ) {
        throw new Error(
          "Your session has expired. Please log in again."
        );
      }

      if (!response.ok) {
        const body = await response
          .json()
          .catch(() => ({}));

        throw new Error(
          body.detail ||
            "Unable to download the submitted file."
        );
      }

      const blob =
        await response.blob();

      const url =
        URL.createObjectURL(blob);

      const link =
        window.document.createElement(
          "a"
        );

      link.href = url;
      link.download =
        document.filename;

      window.document.body.appendChild(
        link
      );

      link.click();
      link.remove();

      URL.revokeObjectURL(url);
    } catch (err) {
      setReviewError(err.message);
    }
  }


  async function handleCommitteeResponse(
    invitation,
    status
  ) {
    setRespondingToInvitation(
      invitation.id
    );

    setInvitationError("");

    try {
      await api(
        `/faculty/committee-invitations/${invitation.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            status,
          }),
        }
      );

      setInvitations(
        (current) =>
          current.filter(
            (item) =>
              item.id !==
              invitation.id
          )
      );

      showToast(
        `You ${status === "approved" ? "accepted" : "declined"} ${invitation.student_name}'s committee invitation.`
      );

      if (status === "approved") {
        try {
          const refreshed =
            await api(
              "/faculty/me/committee-memberships"
            );

          setMemberships(
            refreshed
          );
        } catch {
          // Membership will refresh next time the dashboard loads.
        }
      }
    } catch (err) {
      setInvitationError(
        err.message
      );

      // The student may have removed the invitation,
      // or another response may already have been recorded.
      try {
        const refreshed =
          await api(
            "/faculty/me/committee-invitations"
          );

        setInvitations(
          refreshed
        );
      } catch {
        // Keep the original backend error visible.
      }
    } finally {
      setRespondingToInvitation(
        null
      );
    }
  }


  async function handleLeaveCommittee() {
    const membership =
      membershipToLeave;

    setMembershipToLeave(null);

    setLeavingMembership(
      membership.id
    );

    setMembershipError("");

    try {
      await api(
        `/faculty/committee-memberships/${membership.id}`,
        {
          method: "DELETE",
        }
      );

      setMemberships(
        (current) =>
          current.filter(
            (item) =>
              item.id !==
              membership.id
          )
      );

      showToast(
        `You left ${membership.student_name}'s committee.`
      );
    } catch (err) {
      setMembershipError(
        err.message
      );

      // Refresh in case the membership was already removed.
      try {
        const refreshed =
          await api(
            "/faculty/me/committee-memberships"
          );

        setMemberships(
          refreshed
        );
      } catch {
        // Keep the original backend error visible.
      }
    } finally {
      setLeavingMembership(null);
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

        <p className="mt-3 text-mist/80">
          {error}
        </p>

        <button
          type="button"
          onClick={() =>
            setAttempt(
              (value) => value + 1
            )
          }
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
    // The advisees' presentations. Older backends don't send this, so default to none.
    presentations = [],
  } = data;

  // Scrolls to a review on the Pending reviews list and highlights it for a moment.
  function openReview(item) {
    // The review's id on the page.
    const reviewId = `review-${item.student_id}-${item.milestone_id}`;
    // Scroll to it.
    document.getElementById(reviewId)?.scrollIntoView({ behavior: "smooth", block: "center" });
    // Highlight it.
    setHighlightedId(reviewId);
    // Remove the highlight after a few seconds.
    setTimeout(() => setHighlightedId(null), 3000);
  }


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
          Welcome back,{" "}
          {faculty.full_name}.
        </p>
      </header>


      <section className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-mist/55">
            Assigned students
          </p>

          <p className="mt-3 font-display text-3xl font-bold text-white">
            {
              summary.assigned_students
            }
          </p>

          <p className="mt-1 text-sm text-mist/60">
            Students currently assigned
            to you
          </p>
        </div>

        <div className="rounded-2xl border border-sage/25 bg-panel p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-mist/55">
            Pending reviews
          </p>

          <p className="mt-3 font-display text-3xl font-bold text-sage">
            {
              summary.pending_reviews
            }
          </p>

          <p className="mt-1 text-sm text-mist/60">
            Milestone submissions
            requiring attention
          </p>
        </div>
      </section>


      <section
        id="section-invitations"
        aria-labelledby="committee-invitations-title"
        className={highlightClass(
          "section-invitations"
        )}
      >
        <div className="mb-3 flex items-center gap-2">
          <h2
            id="committee-invitations-title"
            className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70"
          >
            Committee invitations
          </h2>

          <span className="rounded-full bg-panel px-2 py-0.5 text-xs text-mist/60">
            {invitations.length}
          </span>
        </div>

        {invitationError && (
          <p
            role="alert"
            className="mb-3 rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200"
          >
            {invitationError}
          </p>
        )}

        {invitations.length > 0 ? (
          <div className="space-y-2">
            {invitations.map(
              (invitation) => {
                const isResponding =
                  respondingToInvitation ===
                  invitation.id;

                return (
                  <div
                    key={
                      invitation.id
                    }
                    className="rounded-xl border border-line bg-panel p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="font-display font-semibold text-white">
                          {
                            invitation.student_name
                          }
                        </h3>

                        <p className="mt-1 text-sm text-mist/65">
                          Invited you to
                          join their
                          committee
                        </p>

                        <p className="mt-1 text-xs text-mist/45">
                          Invited on{" "}
                          {
                            invitation.invited_on
                          }
                        </p>
                      </div>

                      <span className="rounded-full border border-sage/25 bg-sage/10 px-3 py-1 text-xs text-sage">
                        Pending
                      </span>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={
                          isResponding
                        }
                        onClick={() =>
                          handleCommitteeResponse(
                            invitation,
                            "approved"
                          )
                        }
                        className="rounded-lg bg-sage px-3 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Approve
                      </button>

                      <button
                        type="button"
                        disabled={
                          isResponding
                        }
                        onClick={() =>
                          handleCommitteeResponse(
                            invitation,
                            "declined"
                          )
                        }
                        className="rounded-lg border border-red-400/30 px-3 py-2 text-sm font-semibold text-red-300 hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Decline
                      </button>
                    </div>

                    {isResponding && (
                      <p className="mt-2 text-xs text-mist/50">
                        Updating
                        invitation…
                      </p>
                    )}
                  </div>
                );
              }
            )}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">
            No committee invitations
            are waiting for your
            response.
          </p>
        )}
      </section>


      <section
        id="section-memberships"
        aria-labelledby="committee-memberships-title"
        className={highlightClass(
          "section-memberships"
        )}
      >
        <div className="mb-3 flex items-center gap-2">
          <h2
            id="committee-memberships-title"
            className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70"
          >
            My committee memberships
          </h2>

          <span className="rounded-full bg-panel px-2 py-0.5 text-xs text-mist/60">
            {memberships.length}
          </span>
        </div>

        {membershipError && (
          <p
            role="alert"
            className="mb-3 rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200"
          >
            {membershipError}
          </p>
        )}

        {memberships.length > 0 ? (
          <div className="space-y-2">
            {memberships.map(
              (membership) => {
                const isLeaving =
                  leavingMembership ===
                  membership.id;

                return (
                  <div
                    key={
                      membership.id
                    }
                    className="rounded-xl border border-line bg-panel p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <h3 className="font-display font-semibold text-white">
                          {
                            membership.student_name
                          }
                        </h3>

                        <p className="mt-1 text-sm text-mist/65">
                          Committee member
                        </p>

                        <p className="mt-1 text-xs text-mist/45">
                          Invitation date{" "}
                          {
                            membership.invited_on
                          }
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-3">
                        <span className="rounded-full border border-sage/25 bg-sage/10 px-3 py-1 text-xs text-sage">
                          Approved
                        </span>

                        <button
                          type="button"
                          disabled={
                            isLeaving
                          }
                          onClick={() =>
                            setMembershipToLeave(
                              membership
                            )
                          }
                          className="rounded-lg border border-red-400/30 px-3 py-2 text-sm font-semibold text-red-300 hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isLeaving
                            ? "Leaving…"
                            : "Leave Committee"}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              }
            )}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">
            You are not currently
            serving on any student
            committees.
          </p>
        )}
      </section>


      {/* The advisees' exam, proposal and defense presentations, with what happens next. */}
      <section
        id="section-presentations"
        aria-labelledby="presentations-title"
        className={highlightClass(
          "section-presentations"
        )}
      >
        {/* The heading and count. */}
        <div className="mb-3 flex items-center gap-2">
          <h2
            id="presentations-title"
            className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70"
          >
            Presentations
          </h2>

          <span className="rounded-full bg-panel px-2 py-0.5 text-xs text-mist/60">
            {presentations.length}
          </span>
        </div>

        {presentations.length > 0 ? (
          <div className="space-y-3">
            {presentations.map((item) => {
              // The stage's badge and next step.
              const stage = PRESENTATION_STAGES[item.stage];
              // True once the presentation has taken place.
              const done = item.stage === "held" || item.stage === "revision_requested";
              // True for the student's advisor. Older backends don't send a role, and only listed advisees.
              const isAdvisor = (item.role ?? "advisor") === "advisor";

              return (
                // One card per presentation, outlined in green once it's done.
                <div
                  key={`${item.student_id}-${item.milestone_id}`}
                  className={`rounded-xl border bg-panel p-4 ${done ? "border-sage/50" : "border-line"}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      {/* The student and milestone. */}
                      <h3 className="font-display font-semibold text-white">
                        {item.student_name}
                      </h3>
                      <p className="mt-1 text-sm text-mist/65">
                        {item.milestone_name}
                        {/* Says whether the viewer advises the student or is on the committee. */}
                        {isAdvisor ? " · You're the advisor" : " · You're on the committee"}
                      </p>
                    </div>

                    {/* The stage. */}
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${stage.tone}`}>
                      {stage.badge}
                    </span>
                  </div>

                  {/* The date and place, once a date is chosen. */}
                  {item.scheduled_at && (
                    <p className="mt-3 text-sm text-white">
                      {done ? "Held on " : ""}
                      {formatPresentationDate(item.scheduled_at)}
                      {" · "}
                      {item.mode === "online" ? (
                        // An online presentation links to its meeting.
                        <a href={item.location} target="_blank" rel="noopener noreferrer" className="break-all text-sage underline underline-offset-4 hover:text-sage-light">
                          Zoom meeting
                        </a>
                      ) : item.mode === "hybrid" ? (
                        // A hybrid shows the room and links to the Zoom meeting.
                        <>
                          {item.location}
                          {" or "}
                          <a href={item.meeting_link} target="_blank" rel="noopener noreferrer" className="break-all text-sage underline underline-offset-4 hover:text-sage-light">
                            join by Zoom
                          </a>
                        </>
                      ) : (
                        // An in-person presentation shows its room.
                        item.location
                      )}
                    </p>
                  )}

                  {/* What happens next. */}
                  <p className="mt-2 text-sm text-mist/80">
                    {stage.next(item, isAdvisor)}
                  </p>

                  {/* After the presentation, the advisor goes straight to the decision. */}
                  {item.stage === "held" && isAdvisor && (
                    <button
                      type="button"
                      onClick={() => openReview(item)}
                      className="mt-3 rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink hover:bg-sage-light"
                    >
                      Record final decision
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">
            No presentations in progress. Your students&apos; and committee students&apos; exam, proposal and defense presentations appear here once the advisor approves the document.
          </p>
        )}
      </section>


      <section
        id="section-reviews"
        aria-labelledby="reviews-title"
        className={highlightClass(
          "section-reviews"
        )}
      >
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

        {pending_reviews.length >
        0 ? (
          <div className="space-y-3">
            {pending_reviews.map(
              (review) => {
                const reviewKey =
                  `${review.student_id}-${review.milestone_id}`;

                const isReviewing =
                  reviewing ===
                  reviewKey;

                const reviewSubmissions =
                  submissions[
                    reviewKey
                  ];

                const submissionError =
                  submissionErrors[
                    reviewKey
                  ];

                return (
                  <div
                    key={reviewKey}
                    id={`review-${reviewKey}`}
                    className={`rounded-xl border border-line bg-panel p-4 ${highlightClass(
                      `review-${reviewKey}`
                    )}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="font-display font-semibold text-white">
                          {
                            review.student_name
                          }
                        </h3>

                        <p className="mt-1 text-sm text-mist/65">
                          {
                            review.milestone_name
                          }
                        </p>
                      </div>

                      <span className="rounded-full border border-sage/25 bg-sage/10 px-3 py-1 text-xs text-sage">
                        {STATUS_LABELS[
                          review.status
                        ] ||
                          review.status}
                      </span>
                    </div>


                    <div className="mt-4 rounded-xl border border-line/70 bg-ink/20 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/60">
                        Submitted files
                      </p>

                      {submissionError ? (
                        <p className="mt-3 text-sm text-red-300">
                          Unable to load
                          submitted
                          files:{" "}
                          {
                            submissionError
                          }
                        </p>
                      ) : reviewSubmissions ===
                        undefined ? (
                        <p className="mt-3 text-sm text-mist/50">
                          Loading
                          submitted
                          files…
                        </p>
                      ) : reviewSubmissions.length ===
                        0 ? (
                        <p className="mt-3 text-sm text-mist/50">
                          No submitted
                          files found.
                        </p>
                      ) : (
                        <div className="mt-3 space-y-4">
                          {reviewSubmissions.map(
                            (
                              submission
                            ) => (
                              <div
                                key={
                                  submission.attempt
                                }
                                className="rounded-lg border border-line/60 p-3"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <p className="text-sm font-semibold text-white">
                                    Attempt{" "}
                                    {
                                      submission.attempt
                                    }
                                  </p>

                                  <p className="text-xs text-mist/45">
                                    {new Date(
                                      submission.submitted_at
                                    ).toLocaleString()}
                                  </p>
                                </div>

                                {submission
                                  .documents
                                  .length >
                                0 ? (
                                  <div className="mt-3 space-y-2">
                                    {submission.documents.map(
                                      (
                                        document
                                      ) => (
                                        <div
                                          key={
                                            document.id
                                          }
                                          className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-panel px-3 py-2"
                                        >
                                          <div>
                                            <p className="text-sm text-mist/85">
                                              {
                                                document.filename
                                              }
                                            </p>

                                            <p className="mt-0.5 text-xs text-mist/45">
                                              {Math.max(
                                                1,
                                                Math.round(
                                                  document.size_bytes /
                                                    1024
                                                )
                                              )}{" "}
                                              KB
                                            </p>
                                          </div>

                                          <button
                                            type="button"
                                            onClick={() =>
                                              handleDocumentDownload(
                                                document
                                              )
                                            }
                                            className="rounded-lg border border-sage/30 px-3 py-1.5 text-xs font-semibold text-sage hover:bg-sage/10"
                                          >
                                            Download
                                          </button>
                                        </div>
                                      )
                                    )}
                                  </div>
                                ) : (
                                  <p className="mt-2 text-xs text-mist/50">
                                    This
                                    attempt
                                    has no
                                    attached
                                    files.
                                  </p>
                                )}
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>


                    <div className="mt-4">
                      <label
                        htmlFor={`review-comment-${reviewKey}`}
                        className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/60"
                      >
                        Review comment
                      </label>

                      <textarea
                        id={`review-comment-${reviewKey}`}
                        rows={3}
                        value={
                          reviewComments[
                            reviewKey
                          ] || ""
                        }
                        disabled={
                          isReviewing
                        }
                        onChange={(
                          event
                        ) =>
                          setReviewComments(
                            (
                              current
                            ) => ({
                              ...current,
                              [reviewKey]:
                                event
                                  .target
                                  .value,
                            })
                          )
                        }
                        placeholder="Optional comment for the student"
                        className="mt-2 w-full resize-y rounded-xl border border-line bg-ink/30 px-3 py-2 text-sm text-white outline-none placeholder:text-mist/35 focus:border-sage/50 disabled:cursor-not-allowed disabled:opacity-50"
                      />
                    </div>


                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={
                          isReviewing
                        }
                        onClick={() =>
                          handleReview(
                            review,
                            "approved"
                          )
                        }
                        className="rounded-lg bg-sage px-3 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Approve
                      </button>

                      <button
                        type="button"
                        disabled={
                          isReviewing
                        }
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
                        disabled={
                          isReviewing
                        }
                        onClick={() =>
                          handleReview(
                            review,
                            "rejected"
                          )
                        }
                        className="rounded-lg border border-red-400/30 px-3 py-2 text-sm font-semibold text-red-300 hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </div>

                    {isReviewing && (
                      <p className="mt-2 text-xs text-mist/50">
                        Updating
                        milestone…
                      </p>
                    )}
                  </div>
                );
              }
            )}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">
            No milestone submissions
            are waiting for review.
          </p>
        )}
      </section>


      <section
        id="section-students"
        aria-labelledby="students-title"
        className={highlightClass(
          "section-students"
        )}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
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

          {students.length > 0 && (
            <p className="text-xs text-mist/45">
              Select a student to view
              detailed progress
            </p>
          )}
        </div>

        {students.length > 0 ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {students.map(
              (student) => (
                <Link
                  key={student.id}
                  to={`/faculty/students/${student.id}/progress`}
                  className="group block rounded-xl border border-line bg-panel p-5 transition-colors hover:border-sage/40 hover:bg-panel/80"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-display font-semibold text-white transition-colors group-hover:text-sage">
                        {
                          student.full_name
                        }
                      </h3>

                      <p className="mt-1 text-xs text-mist/50">
                        {student.program_year >
                        0
                          ? `Program Year ${student.program_year}`
                          : student.program_year ===
                            0
                          ? "Not yet started"
                          : "Program year unavailable"}
                      </p>
                    </div>

                    <span className="text-sm font-semibold text-sage">
                      {
                        student.progress_percent
                      }
                      %
                    </span>
                  </div>

                  <div className="mt-4">
                    <ProgressBar
                      value={
                        student.progress_percent
                      }
                    />
                  </div>

                  <div className="mt-3 flex items-center justify-between gap-3">
                    <p className="text-xs text-mist/55">
                      {
                        student.completed_milestones
                      }{" "}
                      of{" "}
                      {
                        student.total_milestones
                      }{" "}
                      milestones approved
                    </p>

                    <span className="shrink-0 text-xs font-semibold text-sage opacity-70 transition-opacity group-hover:opacity-100">
                      View progress →
                    </span>
                  </div>
                </Link>
              )
            )}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-mist/50">
            No students are currently
            assigned to you.
          </p>
        )}
      </section>


      {membershipToLeave && (
        <ConfirmDialog
          title={`Leave ${membershipToLeave.student_name}'s committee?`}
          confirmLabel="Leave"
          onConfirm={
            handleLeaveCommittee
          }
          onCancel={() =>
            setMembershipToLeave(
              null
            )
          }
        />
      )}
    </div>
  );
}
