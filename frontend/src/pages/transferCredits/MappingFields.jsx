import { useId } from "react";

export const FIELD = "mt-1 block w-full rounded-lg border border-line bg-ink px-3 py-2 text-sm text-white focus:border-sage focus:outline-none";
export const BUTTON = "rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50";
export const SECONDARY = "rounded-lg border border-sage/40 bg-sage/10 px-4 py-2 text-sm font-medium text-sage hover:bg-sage/20 disabled:opacity-50";
export const AREAS = { theory: "Theoretical CS", ai_ml: "AI & ML", systems: "Systems" };
export const STATUSES = { pending: "Pending", approved: "Approved", rejected: "Rejected", more_information_required: "More information required" };

export function mappingFrom(value) {
  return {
    category: value.category,
    area: value.area ?? null,
    equivalent_course_id: value.equivalent_course_id ?? null,
    credits: Number(value.credits),
    is_research: Boolean(value.is_research),
  };
}

export function Field({ label, children }) {
  const id = useId();
  // Each caller provides a single render function so labels also work for selects.
  return <div><label htmlFor={id} className="text-sm text-mist">{label}</label>{children(id)}</div>;
}

export function MappingFields({ value, onChange, courses, maxCredits = 19 }) {
  const update = (key, next) => onChange({ ...value, [key]: next });
  const equivalents = courses.filter(course => value.category === "core" ? course.area === "core"
    : value.category === "breadth" ? course.area === value.area : true);
  return <div className="grid gap-4 sm:grid-cols-2">
    <Field label="Category">{id => <select id={id} className={FIELD} value={value.category} onChange={event => onChange({
      ...value, category: event.target.value, area: null, equivalent_course_id: null, is_research: false,
    })}>
      <option value="core">Core</option><option value="breadth">Breadth</option><option value="electives">Electives</option>
    </select>}</Field>
    <Field label="Credits">{id => <input id={id} className={FIELD} type="number" min="1" max={maxCredits} step="1" required value={value.credits} onChange={event => update("credits", event.target.value)} />}</Field>
    {value.category === "breadth" && <Field label="Breadth area">{id => <select id={id} className={FIELD} required value={value.area ?? ""} onChange={event => onChange({ ...value, area: event.target.value, equivalent_course_id: null })}>
      <option value="">Select an area</option>{Object.entries(AREAS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
    </select>}</Field>}
    <Field label={value.category === "core" ? "Equivalent UAlbany course" : "Equivalent UAlbany course (if applicable)"}>{id => <select id={id} className={FIELD} required={value.category === "core"} value={value.equivalent_course_id ?? ""} onChange={event => {
      const course = courses.find(item => item.id === Number(event.target.value));
      onChange({ ...value, equivalent_course_id: course?.id ?? null, is_research: value.category === "electives" && Boolean(course?.is_research) });
    }}>
      <option value="">{value.category === "core" ? "Select an equivalent course" : "No specific equivalent"}</option>
      {equivalents.map(course => <option key={course.id} value={course.id}>{course.code} — {course.title}</option>)}
    </select>}</Field>
    {value.category === "electives" && <label className="flex items-center gap-2 text-sm sm:col-span-2"><input type="checkbox" checked={value.is_research} onChange={event => update("is_research", event.target.checked)} />Independent study or research (existing 15-credit elective limit applies)</label>}
  </div>;
}

export function MappingSummary({ mapping, courses }) {
  const course = courses.find(item => item.id === mapping.equivalent_course_id);
  return <p className="text-sm text-mist">{mapping.credits} credits · {mapping.category === "core" ? "Core" : mapping.category === "breadth" ? `Breadth — ${AREAS[mapping.area]}` : "Electives"}
    {course && ` · Equivalent to ${course.code}`}{mapping.is_research && " · Research"}</p>;
}
