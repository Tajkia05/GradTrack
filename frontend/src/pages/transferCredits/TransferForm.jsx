import { useState } from "react";
import { api } from "../../api/client.js";
import { BUTTON, FIELD, SECONDARY, Field, MappingFields, mappingFrom } from "./MappingFields.jsx";

const GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E", "S", "U"];
const EMPTY = { institution: "", course_code: "", course_title: "", completed_on: "", grade: "", category: "electives", credits: 3, area: null, equivalent_course_id: null, is_research: false };

function encodeFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ filename: file.name, data_base64: String(reader.result).split(",")[1] });
    reader.onerror = () => reject(new Error(`Unable to read ${file.name}. Choose the file again.`));
    reader.readAsDataURL(file);
  });
}

export default function TransferForm({ request, courses, onSaved, onCancel }) {
  const [form, setForm] = useState(request?.requested ?? EMPTY);
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const update = (key, value) => setForm(current => ({ ...current, [key]: value }));

  function chooseFiles(event) {
    const chosen = Array.from(event.target.files);
    setError("");
    if (chosen.length > 5 || chosen.some(file => file.size > 10 * 1024 * 1024)) {
      setError("Choose up to 5 files, no larger than 10 MB each.");
      setFiles([]);
      event.target.value = "";
      return;
    }
    setFiles(chosen);
  }

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const encoded = await Promise.all(files.map(encodeFile));
      const endpoint = request ? `/students/me/transfer-credits/${request.id}/resubmit` : "/students/me/transfer-credits";
      const result = await api(endpoint, { method: "POST", body: JSON.stringify({ ...form, ...mappingFrom(form), files: encoded, version: request?.version ?? null }) });
      onSaved(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return <form onSubmit={submit} className="space-y-5">
    <p className="text-sm text-mist/70">Submit one completed course from the last five years. The Program Director reviews your proposed category, equivalence and credits. CSI 790 and CSI 898 cannot be replaced.</p>
    {request && <p className="rounded-lg border border-line p-3 text-sm">Previous submissions and documents remain in the history. Attach the complete supporting documents for this revision.</p>}
    <fieldset disabled={busy} className="space-y-5 disabled:opacity-60">
      <div className="grid gap-4 sm:grid-cols-2">
        {[['institution', 'Previous institution', 255], ['course_code', 'Previous course code', 20], ['course_title', 'Previous course title', 255]].map(([key, label, max]) => <Field key={key} label={label}>{id => <input id={id} required maxLength={max} className={FIELD} value={form[key]} onChange={event => update(key, event.target.value)} />}</Field>)}
        <Field label="Completion date">{id => <input id={id} type="date" required className={FIELD} value={form.completed_on} onChange={event => update("completed_on", event.target.value)} />}</Field>
        <Field label="Final grade">{id => <select id={id} className={FIELD} required value={form.grade} onChange={event => update("grade", event.target.value)}><option value="">Select a grade</option>{GRADES.map(grade => <option key={grade}>{grade}</option>)}</select>}</Field>
      </div>
      <section className="space-y-3 rounded-xl border border-line p-4">
        <h3 className="font-display font-semibold text-white">Requested credit</h3>
        <MappingFields value={form} onChange={setForm} courses={courses} />
        <p className="text-xs text-mist/60">Core and Breadth require B or better (or S). Letter grades count toward GPA. Existing coursework requirements and averages still apply.</p>
      </section>
      <Field label="Supporting documents">{id => <input id={id} className={FIELD} type="file" multiple required accept=".pdf,.docx,.pptx,.png" onChange={chooseFiles} />}</Field>
      <p className="text-xs text-mist/60">Include a syllabus, transcript or other evidence. PDF, DOCX, PPTX or PNG · 1–5 files · up to 10 MB each.</p>
    </fieldset>
    {error && <p role="alert" className="text-sm text-amber-200">{error}</p>}
    <div className="flex justify-end gap-3">
      <button type="button" disabled={busy} onClick={onCancel} className={SECONDARY}>Cancel</button>
      <button disabled={busy || !files.length} className={BUTTON}>{busy ? "Submitting…" : request ? "Resubmit request" : "Submit request"}</button>
    </div>
  </form>;
}
