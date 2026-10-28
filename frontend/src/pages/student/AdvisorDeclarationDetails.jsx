import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client.js";
import { AcademicDetails } from "./AdvisorDeclaration.jsx";

export default function AdvisorDeclarationDetails() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    const overflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    return () => { dialog.close(); document.body.style.overflow = overflow; };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setData(null);
    setError("");
    api("/students/me/advisor", { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setData(result); })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [open, attempt]);

  function handleKeyDown(event) {
    if (event.key !== "Tab") return;
    const controls = [...dialogRef.current.querySelectorAll("button, a[href]")]
      .filter((element) => element.getClientRects().length > 0);
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  return <>
    <button type="button" aria-haspopup="dialog" aria-label="Details of advisor declaration" onClick={() => setOpen(true)} className="cursor-pointer rounded-lg border border-sage/40 bg-sage/10 px-4 py-2 text-sm font-medium text-sage hover:bg-sage/20">Details</button>
    <dialog ref={dialogRef} aria-labelledby="declaration-details-title" onKeyDown={handleKeyDown} onCancel={(event) => { event.preventDefault(); setOpen(false); }} className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded-2xl border border-sage/30 bg-panel p-0 text-mist shadow-2xl backdrop:bg-black/75 backdrop:backdrop-blur-sm">
      <header className="flex items-start justify-between gap-4 border-b border-line p-5 sm:p-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-sage">Completed milestone</p>
          <h2 id="declaration-details-title" className="mt-2 font-display text-2xl font-bold text-white">Advisor declaration</h2>
        </div>
        <button type="button" onClick={() => setOpen(false)} aria-label="Close declaration details" className="rounded-lg border border-line px-3 py-1 text-xl hover:border-sage">×</button>
      </header>
      <div className="space-y-5 p-5 sm:p-6">
        {error ? <div role="alert">
          <p className="text-sm text-red-300">{error}</p>
          <button type="button" onClick={() => setAttempt((value) => value + 1)} className="mt-3 text-sm text-sage underline">Try again</button>
        </div> : !data ? <p role="status" className="text-sm text-mist/70">Loading declaration details…</p> : <>
          <div className="rounded-xl border border-sage/25 bg-sage/5 p-4">
            <p className="text-sm text-mist/70">Declaration date</p>
            <p className="mt-1 font-display text-lg font-semibold text-white">{data.declared_on
              ? <time dateTime={data.declared_on}>{new Intl.DateTimeFormat("en-US", { dateStyle: "long" }).format(new Date(`${data.declared_on}T12:00:00`))}</time>
              : "Date not recorded"}</p>
            <p className="mt-2 text-xs text-mist/60">Declaration completed. No faculty approval was required.</p>
          </div>
          <section aria-label="Assigned advisor" className="overflow-hidden rounded-xl border border-line">
            <div className="p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-sage">Your advisor</p>
              <h3 className="mt-2 font-display text-xl font-semibold text-white">{data.advisor.full_name}</h3>
              <p className="mt-1 break-all text-sm text-mist/70">{data.advisor.email}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full border border-line px-3 py-1">{data.advisor.advisee_count} assigned student{data.advisor.advisee_count === 1 ? "" : "s"}</span>
                <span className="rounded-full border border-line px-3 py-1">{data.advisor.accepting_students === true ? "Accepting students" : data.advisor.accepting_students === false ? "Not accepting new students" : "Availability not provided"}</span>
              </div>
            </div>
            <AcademicDetails advisor={data.advisor} />
          </section>
          <p className="text-xs text-mist/60">Advisor information reflects their current profile.</p>
        </>}
      </div>
      <footer className="sticky bottom-0 flex justify-end border-t border-line bg-panel p-5">
        <button type="button" onClick={() => setOpen(false)} className="rounded-lg bg-sage px-5 py-2 text-sm font-semibold text-ink hover:bg-sage-light">Close</button>
      </footer>
    </dialog>
  </>;
}
