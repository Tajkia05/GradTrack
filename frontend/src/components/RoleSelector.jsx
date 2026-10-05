// RoleSelector.jsx — THE THREE ROLE BUTTONS: Student / Faculty / Program Director.
// Used on both the Login and Register pages.
//
// How to use it:
//   const [role, setRole] = useState("student");
//   <RoleSelector value={role} onChange={setRole} />
//
// The green highlight is ONE separate block that slides behind the buttons
// to whichever one is selected, so switching roles looks smooth.

import { ROLES } from "../auth/roles.js";

export default function RoleSelector({ value, onChange }) {
  // Which position is selected: 0 = Student, 1 = Faculty, 2 = Program Director.
  const selectedIndex = Math.max(0, ROLES.findIndex((r) => r.value === value));

  return (
    <div className="mb-4">
      {/* <p className="mb-1 text-sm font-medium">I am a...</p> */}
      {/* role="radiogroup": tells screen readers "pick exactly one of these". */}
      <div
        role="radiogroup"
        aria-label="Choose your role"
        className="relative grid grid-cols-3 rounded-lg border border-line bg-ink p-1"
      >
        {/* The sliding green highlight.
            It is one-third wide, and moves right by its own width for each step:
            Student → 0%, Faculty → 100%, Program Director → 200%. */}
        <div
          aria-hidden="true"
          className="absolute bottom-1 left-1 top-1 rounded-md bg-sage transition-transform duration-300 ease-out motion-reduce:transition-none"
          style={{
            width: "calc((100% - 0.5rem) / 3)",
            transform: `translateX(${selectedIndex * 100}%)`,
          }}
        />

        {ROLES.map((r) => {
          const selected = value === r.value;
          return (
            <button
              key={r.value}
              type="button" // "button" so clicking it does NOT submit the form
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(r.value)}
              // "relative" puts the text ABOVE the sliding highlight.
              // The text color fades smoothly: dark on green when selected, light otherwise.
              className={
                "relative rounded-md px-2 py-2 text-sm leading-tight transition-colors duration-300 " +
                (selected ? "font-semibold text-ink" : "text-mist/70 hover:text-white")
              }
            >
              {r.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
