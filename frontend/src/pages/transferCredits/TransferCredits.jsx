import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, getToken } from "../../api/client.js";
import ConfirmDialog from "../../components/ConfirmDialog.jsx";
import TransferForm from "./TransferForm.jsx";
import { BUTTON, FIELD, SECONDARY, STATUSES, Field, MappingFields, MappingSummary, mappingFrom } from "./MappingFields.jsx";

function formatDate(value) {
  return new Date(value.length === 10 ? `${value}T12:00:00` : value).toLocaleString("en-US", value.length === 10 ? { dateStyle: "medium" } : { dateStyle: "medium", timeStyle: "short" });
}

function Modal({ title, children, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    const overflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    return () => { dialog.close(); document.body.style.overflow = overflow; };
  }, []);
  return <dialog ref={ref} aria-labelledby="transfer-dialog-title" onCancel={event => { event.preventDefault(); onClose(); }} className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-2xl border border-sage/30 bg-panel p-0 text-mist shadow-2xl backdrop:bg-black/75 backdrop:backdrop-blur-sm">
    <header className="flex items-start justify-between gap-4 border-b border-line p-5"><h2 id="transfer-dialog-title" className="font-display text-2xl font-bold text-white">{title}</h2><button type="button" aria-label="Close transfer request" onClick={onClose} className="rounded-lg border border-line px-3 py-1 text-xl hover:border-sage">×</button></header>
    <div className="space-y-5 p-5">{children}</div>
  </dialog>;
}

function ReviewForm({ request, courses, onSaved }) {
  const [mapping, setMapping] = useState(mappingFrom(request.requested));
  const [decision, setDecision] = useState("approved");
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const adjusted = JSON.stringify(mappingFrom(mapping)) !== JSON.stringify(mappingFrom(request.requested));

  async function save() {
    setConfirming(false);
    setBusy(true);
    setError("");
    try {
      const result = await api(`/director/transfer-credits/${request.id}/decision`, {
        method: "POST", body: JSON.stringify({ version: request.version, decision, comment, mapping: decision === "approved" ? mappingFrom(mapping) : null }),
      });
      onSaved(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return <form className="space-y-4 rounded-xl border border-sage/30 p-4" onSubmit={event => { event.preventDefault(); setConfirming(true); }}>
    <h3 className="font-display text-lg font-semibold text-white">Record a decision</h3>
    <fieldset disabled={busy} className="space-y-4">
      <Field label="Decision">{id => <select id={id} className={FIELD} value={decision} onChange={event => setDecision(event.target.value)}><option value="approved">Approve</option><option value="more_information_required">Request more information</option><option value="rejected">Reject</option></select>}</Field>
      {decision === "approved" && <MappingFields value={mapping} onChange={setMapping} courses={courses} maxCredits={request.requested.credits} />}
      <Field label="Review comment">{id => <textarea id={id} className={FIELD} rows="3" maxLength="4000" required={decision !== "approved" || adjusted} value={comment} onChange={event => setComment(event.target.value)} />}</Field>
      <p className="text-xs text-mist/60">Explain adjustments, rejections and requests for more information. Approval applies the recognized credit to Coursework. Rejection closes this request.</p>
      <button className={BUTTON} disabled={busy}>{busy ? "Saving…" : "Record decision"}</button>
    </fieldset>
    {error && <p role="alert" className="text-sm text-amber-200">{error}</p>}
    {confirming && <ConfirmDialog title={`Confirm ${STATUSES[decision].toLowerCase()} decision?`} message={decision === "approved" ? "This decision applies credit to Coursework and becomes final." : "The student will receive your decision and comment."} confirmLabel="Confirm decision" onConfirm={save} onCancel={() => setConfirming(false)} />}
  </form>;
}

function RequestDetails({ request, courses, director, canSubmit, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");

  async function download(file) {
    setError("");
    try {
      const response = await fetch(`/api/transfer-credit-documents/${file.id}`, { headers: { Authorization: `Bearer ${getToken()}` } });
      if (!response.ok) throw new Error("Unable to download this document. Refresh and try again.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = file.filename;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err.message);
    }
  }

  if (editing) return <TransferForm request={request} courses={courses} onCancel={() => setEditing(false)} onSaved={result => { setEditing(false); onSaved(result); }} />;
  const details = request.requested;
  return <>
    <div className="rounded-xl border border-line p-4">
      {director && <p className="mb-2 font-semibold text-white">{request.student_name} <span className="font-normal text-mist/60">· {request.student_email}</span></p>}
      <p className="font-medium text-sage">{STATUSES[request.status]}</p>
      <p className="mt-2 font-display text-lg font-semibold text-white">{details.course_code} — {details.course_title}</p>
      <p className="mt-1 text-sm text-mist/70">{details.institution} · Completed {formatDate(details.completed_on)} · Grade {details.grade}</p>
      <h3 className="mb-2 mt-4 font-semibold text-white">Requested credit</h3>
      <MappingSummary mapping={details} courses={courses} />
      {request.approved && <><h3 className="mb-2 mt-4 font-semibold text-sage">Approved credit</h3><MappingSummary mapping={request.approved} courses={courses} /><p className="mt-2 text-xs text-mist/60">Applied to Coursework. Letter grades contribute to the existing GPA calculation.</p></>}
    </div>
    {!director && canSubmit && request.status === "more_information_required" && <button onClick={() => setEditing(true)} className={BUTTON}>Provide more information</button>}
    <section className="space-y-3">
      <h3 className="font-display text-lg font-semibold text-white">Submissions and documents</h3>
      {request.submissions.map((submission, index) => <details key={submission.id} open={index === 0} className="rounded-xl border border-line p-4">
        <summary className="cursor-pointer font-medium">Submission {submission.version} · {formatDate(submission.submitted_at)}</summary>
        <div className="mt-3 space-y-2 text-sm">
          <p>{submission.details.institution} · {submission.details.course_code} — {submission.details.course_title}</p>
          <p>Completed {formatDate(submission.details.completed_on)} · Grade {submission.details.grade}</p>
          <MappingSummary mapping={submission.details} courses={courses} />
          {submission.documents.map(file => <button key={file.id} type="button" onClick={() => download(file)} className="block break-all text-left text-sage underline underline-offset-4">{file.filename} · {Math.max(1, Math.round(file.size_bytes / 1024))} KB</button>)}
        </div>
      </details>)}
    </section>
    {error && <p role="alert" className="text-sm text-amber-200">{error}</p>}
    <section>
      <h3 className="font-display text-lg font-semibold text-white">History</h3>
      <ol className="mt-3 space-y-3">{request.history.map((entry, index) => <li key={index} className="rounded-xl border border-line p-3 text-sm">
        <p><strong>{STATUSES[entry.status]}</strong> · {entry.changed_by}</p><p className="mt-1 text-xs text-mist/60">{formatDate(entry.changed_at)}</p>
        {entry.comment && <p className="mt-2 whitespace-pre-wrap break-words text-mist">{entry.comment}</p>}
      </li>)}</ol>
    </section>
    {director && request.status === "pending" && <ReviewForm key={request.version} request={request} courses={courses} onSaved={onSaved} />}
  </>;
}

export default function TransferCredits({ director = false }) {
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("request");
  const [data, setData] = useState(null);
  const [courses, setCourses] = useState([]);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [notice, setNotice] = useState("");
  const [creating, setCreating] = useState(false);
  const [filter, setFilter] = useState("all");
  const [reload, setReload] = useState(0);
  const endpoint = director ? "/director/transfer-credits" : "/students/me/transfer-credits";

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    Promise.all([api(endpoint, { signal: controller.signal }), api("/transfer-credits/options", { signal: controller.signal })])
      .then(([result, options]) => { setData(result); setCourses(options); })
      .catch(err => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [endpoint, reload]);

  useEffect(() => {
    setDetail(null);
    setDetailError("");
    if (!selectedId) return;
    const controller = new AbortController();
    api(`${endpoint}/${encodeURIComponent(selectedId)}`, { signal: controller.signal })
      .then(setDetail).catch(err => { if (!controller.signal.aborted) setDetailError(err.message); });
    return () => controller.abort();
  }, [selectedId, endpoint, reload]);

  function closeDetail() {
    setParams(current => { const next = new URLSearchParams(current); next.delete("request"); return next; });
  }

  function saved(result) {
    setCreating(false);
    setNotice(result.status === "pending" ? "Request submitted to the Program Director." : "Decision saved and the student notified.");
    setParams({ request: String(result.id) });
    setReload(value => value + 1);
  }

  const requests = data?.requests.filter(request => filter === "all" || request.status === filter) ?? [];
  return <div className="space-y-6">
    {!director && <Link to="/student" className="text-sm text-sage underline underline-offset-4">← My progress</Link>}
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div><h1 className="font-display text-3xl font-bold text-white">{director ? "Director Dashboard" : "Transfer credits"}</h1><p className="mt-2 text-sm text-mist/65">{director ? "Review prior coursework and record transfer-credit decisions." : "Request credit for prior coursework and track your Program Director’s decision."}</p></div>
      {!director && data?.can_submit && <button onClick={() => setCreating(true)} className={BUTTON}>New transfer request</button>}
    </header>
    {notice && <p role="status" className="rounded-xl border border-sage/30 bg-sage/10 p-4 text-sage">{notice}</p>}
    {error && <div role="alert" className="rounded-xl border border-line p-4 text-amber-200"><p>{error}</p><button className={`${SECONDARY} mt-3`} onClick={() => setReload(value => value + 1)}>Try again</button></div>}
    {!data && !error && <p role="status">Loading transfer requests…</p>}
    {data && <>
      {!director && !data.can_submit && <p className="rounded-xl border border-line p-4 text-sm text-mist/70">New transfer requests require admission with advanced standing.</p>}
      <div className="flex flex-wrap items-center justify-between gap-4"><h2 className="font-display text-lg font-semibold text-white">{director ? "Transfer credit requests" : "My requests"}</h2><Field label="Filter by status">{id => <select id={id} className={FIELD} value={filter} onChange={event => setFilter(event.target.value)}><option value="all">All statuses</option>{Object.entries(STATUSES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>}</Field></div>
      {requests.length === 0 && <p className="rounded-xl border border-dashed border-line p-6 text-mist/60">No transfer requests match this view.</p>}
      <div className="space-y-3">{requests.map(request => <article key={request.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-line bg-panel p-5">
        <div className="min-w-0 flex-1 basis-60"><h3 className="break-words font-display font-semibold text-white">{request.requested.course_code} — {request.requested.course_title}</h3><p className="mt-1 text-sm text-mist/60">{director ? `${request.student_name} · ` : ""}{request.requested.institution}</p><p className="mt-2 text-sm text-mist/70">{request.requested.credits} credits requested · {formatDate(request.submitted_at)}</p></div>
        <span className={`rounded-full border border-line px-3 py-1 text-xs ${request.status === "approved" ? "text-sage" : "text-mist"}`}>{STATUSES[request.status]}</span>
        <button onClick={() => setParams({ request: String(request.id) })} className={SECONDARY}>{director && request.status === "pending" ? "Review request" : "View details"}</button>
      </article>)}</div>
    </>}
    {creating && <Modal title="New transfer request" onClose={() => setCreating(false)}><TransferForm courses={courses} onSaved={saved} onCancel={() => setCreating(false)} /></Modal>}
    {selectedId && <Modal title={`Transfer request #${selectedId}`} onClose={closeDetail}>
      {detailError ? <div role="alert"><p className="text-amber-200">{detailError}</p><button className={`${SECONDARY} mt-3`} onClick={() => setReload(value => value + 1)}>Refresh request</button></div>
        : detail ? <RequestDetails key={`${detail.id}-${detail.version}-${detail.status}`} request={detail} courses={courses} director={director} canSubmit={data?.can_submit} onSaved={saved} /> : <p role="status">Loading request…</p>}
    </Modal>}
  </div>;
}
