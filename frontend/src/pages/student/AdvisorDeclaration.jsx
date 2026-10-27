// Select a real faculty member in a native, keyboard-accessible modal.
import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client.js";

function academicLink(value) {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

function AcademicDetails({ advisor }) {
  const link = academicLink(advisor.academic_url);
  const fields = [["Department", advisor.department], ["Institution / affiliation", advisor.affiliation],
    ["Research interests", advisor.research_interests], ["Laboratory / group", advisor.lab_name]];
  return <section aria-label={`Academic profile of ${advisor.full_name}`} className="border-t border-line px-4 py-3">
    <h3 className="text-sm font-medium text-sage">Academic profile</h3>
    <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
      {fields.map(([label, value]) => <div key={label} className="min-w-0">
        <dt className="text-xs text-mist/60">{label}</dt>
        <dd className="mt-1 whitespace-pre-wrap break-words text-mist">{value || "Not provided"}</dd>
      </div>)}
    </dl>
    {advisor.bio && <p className="mt-4 whitespace-pre-wrap break-words text-sm leading-relaxed text-mist/80">{advisor.bio}</p>}
    {link && <a href={link} target="_blank" rel="noopener noreferrer" className="mt-4 inline-block text-sm text-sage underline underline-offset-4">View academic website ↗<span className="sr-only"> (opens in a new tab)</span></a>}
  </section>;
}

export default function AdvisorDeclaration({ onDeclared }) {
  const [open, setOpen] = useState(false);
  const [advisors, setAdvisors] = useState([]);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const savingRef = useRef(false);
  const dialogRef = useRef(null);
  const searchRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    const previousOverflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    searchRef.current?.focus();
    return () => {
      dialog.close();
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    api("/students/me/advisors", { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setAdvisors(result); })
      .catch((err) => { if (!controller.signal.aborted) { setAdvisors([]); setError(err.message); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [open, attempt]);

  function cancel() {
    if (savingRef.current) return;
    setOpen(false);
    setSelected("");
    setQuery("");
    setError("");
  }

  function keepFocusInDialog(event) {
    if (event.key !== "Tab") return;
    const controls = [...dialogRef.current.querySelectorAll("button:not(:disabled), input:not(:disabled), summary, a[href]")]
      .filter((element) => element.getClientRects().length > 0);
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (!first) { event.preventDefault(); return; }
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!selected || savingRef.current) return;
    savingRef.current = true;
    setSaving(true);
    setError("");
    try {
      const dashboard = await api("/students/me/advisor", {
        method: "PUT", body: JSON.stringify({ advisor_id: Number(selected) }),
      });
      // Close before the parent's success message takes keyboard focus.
      dialogRef.current.close();
      onDeclared(dashboard);
    } catch (err) {
      setError(err.message);
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  const advisor = advisors.find((item) => String(item.id) === selected);
  const filtered = advisors.filter((item) => [item.full_name, item.email, item.department, item.affiliation, item.research_interests, item.lab_name].filter(Boolean).join(" ").toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <>
      <aside aria-labelledby="advisor-title" className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-dashed border-sage/40 bg-sage/5 p-5">
        <div>
          <h2 id="advisor-title" className="font-display text-lg font-semibold text-white">Declare your advisor</h2>
          <p className="mt-1 text-sm text-mist/70">Explore faculty members and choose your research advisor.</p>
        </div>
        <button type="button" onClick={() => { setLoading(true); setOpen(true); }} aria-haspopup="dialog" className="rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink transition hover:bg-sage-light">Choose advisor</button>
      </aside>

      <dialog ref={dialogRef} aria-labelledby="advisor-modal-title" aria-describedby="advisor-modal-description" onKeyDown={keepFocusInDialog} onCancel={(event) => { event.preventDefault(); cancel(); }} className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded-2xl border border-sage/30 bg-panel p-0 text-mist shadow-2xl backdrop:bg-black/75 backdrop:backdrop-blur-sm">
        <form onSubmit={handleSubmit} aria-busy={saving}>
          <div className="flex items-start justify-between gap-4 border-b border-line p-5 sm:p-6">
            <div>
              <p className="text-xs font-medium uppercase tracking-widest text-sage">Your research journey</p>
              <h2 id="advisor-modal-title" className="mt-2 font-display text-2xl font-bold text-white">Choose your advisor</h2>
              <p id="advisor-modal-description" className="mt-2 text-sm text-mist/70">Find a faculty member and review your selection before confirming.</p>
            </div>
            <button type="button" disabled={saving} onClick={cancel} aria-label="Close advisor selection" className="rounded-lg border border-line px-3 py-1 text-xl text-mist hover:border-sage disabled:opacity-50">×</button>
          </div>

          <div className="space-y-4 p-5 sm:p-6">
            <div>
              <label htmlFor="advisor-search" className="mb-2 block text-sm font-medium">Search faculty</label>
              <input ref={searchRef} id="advisor-search" type="search" placeholder="Name, department, or research area" value={query} disabled={saving} onChange={(event) => setQuery(event.target.value)} className="w-full rounded-lg border border-line bg-ink px-4 py-3 text-white outline-none focus:border-sage focus:ring-2 focus:ring-sage/30" />
            </div>
            {error && <p role="alert" className="rounded-lg border border-red-300/25 bg-red-300/5 p-3 text-sm text-red-300">{error}</p>}
            {loading ? <p role="status" className="py-5 text-sm text-mist/70">Loading faculty members…</p> : <>
              <p role="status" className="text-xs text-mist/60">{filtered.length} faculty member{filtered.length === 1 ? "" : "s"} found</p>
              <fieldset disabled={saving} className="space-y-3">
                <legend className="sr-only">Research advisor</legend>
                {filtered.map((item) => {
                  const checked = selected === String(item.id);
                  const unavailable = item.accepting_students === false;
                  return <div key={item.id} className={`rounded-xl border transition focus-within:ring-2 focus-within:ring-sage/60 ${checked ? "border-sage bg-sage/10" : "border-line bg-ink/40 hover:border-sage/50"}`}>
                    <label className={`flex items-start gap-3 p-4 ${unavailable ? "cursor-not-allowed" : "cursor-pointer"}`}>
                    <input type="radio" name="advisor" value={item.id} checked={checked} disabled={unavailable} onChange={() => setSelected(String(item.id))} className="mt-1 h-4 w-4 shrink-0 accent-sage" />
                    <span className="min-w-0 flex-1">
                      <span className="block font-display text-lg font-semibold text-white">{item.full_name}</span>
                      <span className="mt-1 block break-all text-sm text-mist/70">{item.email}</span>
                      {(item.department || item.affiliation) && <span className="mt-2 block break-words text-sm text-mist/80">{[item.department, item.affiliation].filter(Boolean).join(" · ")}</span>}
                      <span className="mt-3 flex flex-wrap gap-2 text-xs">
                        <span className="rounded-full border border-line px-2.5 py-1 text-mist">Faculty</span>
                        <span className="rounded-full border border-sage/20 bg-sage/5 px-2.5 py-1 text-sage">{item.advisee_count} assigned student{item.advisee_count === 1 ? "" : "s"}</span>
                        <span className={`rounded-full border px-2.5 py-1 ${unavailable ? "border-amber-200/25 text-amber-200" : item.accepting_students === true ? "border-sage/25 text-sage" : "border-line text-mist/60"}`}>{item.accepting_students === true ? "Accepting students" : unavailable ? "Not accepting students" : "Availability not provided"}</span>
                      </span>
                    </span>
                    {checked && <span aria-hidden="true" className="text-sage">✓</span>}
                    </label>
                    <AcademicDetails advisor={item} />
                  </div>;
                })}
              </fieldset>
              {filtered.length === 0 && <div className="rounded-xl border border-dashed border-line p-5 text-sm text-mist/70">
                {advisors.length > 0 ? "No matches. Try a different name, department, or research area." : error ? "The faculty list could not be loaded." : "No faculty members are available yet. Contact your program coordinator."}
                {advisors.length > 0 ? <button type="button" onClick={() => setQuery("")} className="mt-3 block text-sage underline">Clear search</button> : <button type="button" onClick={() => setAttempt((value) => value + 1)} className="mt-3 block text-sage underline">Refresh faculty list</button>}
              </div>}
            </>}
            {advisor && <div className="rounded-xl border border-sage/25 bg-sage/5 p-4">
              <p className="text-sm text-sage">Your selection</p>
              <p className="mt-1 font-display text-lg font-semibold text-white">{advisor.full_name}</p>
              <p className="mt-2 text-sm leading-relaxed text-mist/80">Confirming sets your advisor immediately and completes the Advisor declaration milestone. No approval is required.</p>
              <p className="mt-2 text-xs text-mist/60">To change your advisor later, contact your program coordinator.</p>
            </div>}
          </div>

          <div className="sticky bottom-0 flex flex-wrap justify-end gap-3 border-t border-line bg-panel p-5 sm:px-6">
            <button type="button" disabled={saving} onClick={cancel} className="rounded-lg border border-line px-4 py-2 text-sm text-mist hover:border-sage disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={!advisor || advisor.accepting_students === false || saving || loading} className="rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50">{saving ? "Declaring advisor…" : "Confirm declaration"}</button>
          </div>
        </form>
      </dialog>
    </>
  );
}
