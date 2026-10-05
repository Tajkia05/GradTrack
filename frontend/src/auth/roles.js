// roles.js — THE THREE USER ROLES, IN ONE PLACE.
// "value" is what the backend uses; "label" is what people see on screen.

export const ROLES = [
  { value: "student", label: "Student" },
  { value: "faculty", label: "Faculty" },
  { value: "program_director", label: "Program Director" },
];

// Turn "program_director" into "Program Director" for showing on screen.
export function roleLabel(value) {
  return ROLES.find((r) => r.value === value)?.label ?? value;
}
