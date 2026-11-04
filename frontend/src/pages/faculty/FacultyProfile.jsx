import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client.js";
import { useToast } from "../../components/Toast.jsx";


const EMPTY_PROFILE = {
  full_name: "",
  email: "",
  title: "",
  department: "",
  affiliation: "",
  research_interests: "",
  lab_name: "",
  accepting_students: null,
  academic_url: "",
  bio: "",
};


export default function FacultyProfile() {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(EMPTY_PROFILE);
  const [editing, setEditing] = useState(false);
  const [loadingError, setLoadingError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const showToast = useToast();


  useEffect(() => {
    const controller = new AbortController();

    api("/faculty/me/profile", {
      signal: controller.signal,
    })
      .then((data) => {
        if (controller.signal.aborted) return;

        setProfile(data);

        setForm({
          ...EMPTY_PROFILE,
          ...data,
        });
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setLoadingError(err.message);
        }
      });

    return () => controller.abort();
  }, []);


  function handleChange(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }


  function startEditing() {
    setForm({
      ...EMPTY_PROFILE,
      ...profile,
    });

    setSaveError("");
    setEditing(true);
  }


  function cancelEditing() {
    setForm({
      ...EMPTY_PROFILE,
      ...profile,
    });

    setSaveError("");
    setEditing(false);
  }


  async function handleSubmit(event) {
    event.preventDefault();

    const fullName = form.full_name.trim();

    if (!fullName) {
      setSaveError("Full name is required.");
      return;
    }

    setSaving(true);
    setSaveError("");

    try {
      const updated = await api(
        "/faculty/me/profile",
        {
          method: "PUT",
          body: JSON.stringify({
            full_name: fullName,
            title: form.title?.trim() || null,
            department:
              form.department?.trim() || null,
            affiliation:
              form.affiliation?.trim() || null,
            research_interests:
              form.research_interests?.trim() || null,
            lab_name:
              form.lab_name?.trim() || null,
            accepting_students:
              form.accepting_students,
            academic_url:
              form.academic_url?.trim() || null,
            bio: form.bio?.trim() || null,
          }),
        }
      );

      setProfile(updated);

      setForm({
        ...EMPTY_PROFILE,
        ...updated,
      });

      setEditing(false);
      showToast("Profile saved successfully.");
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }


  if (loadingError) {
    return (
      <div className="rounded-2xl border border-line bg-panel p-6">
        <h1 className="font-display text-2xl font-bold text-white">
          Unable to load faculty profile
        </h1>

        <p
          role="alert"
          className="mt-3 text-sm text-red-300"
        >
          {loadingError}
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


  if (!profile) {
    return (
      <div
        role="status"
        className="rounded-2xl border border-line bg-panel p-8 text-mist/70"
      >
        Loading faculty profile…
      </div>
    );
  }


  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <Link
          to="/faculty"
          className="text-sm font-semibold text-sage hover:text-sage-light"
        >
          ← Back to Faculty Dashboard
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-sage">
            Faculty profile
          </p>

          <h1 className="mt-2 font-display text-3xl font-bold text-white">
            {profile.full_name}
          </h1>

          <p className="mt-2 text-sm text-mist/65">
            {profile.title ||
              "Faculty member"}
            {profile.department
              ? ` · ${profile.department}`
              : ""}
          </p>
        </div>

        {!editing && (
          <button
            type="button"
            onClick={startEditing}
            className="rounded-lg bg-sage px-4 py-2 text-sm font-semibold text-ink hover:bg-sage-light"
          >
            Edit profile
          </button>
        )}
      </header>

      {!editing ? (
        <div className="grid gap-4 md:grid-cols-2">
          <ProfileItem
            label="Email"
            value={profile.email}
          />

          <ProfileItem
            label="Title / Designation"
            value={profile.title}
          />

          <ProfileItem
            label="Department"
            value={profile.department}
          />

          <ProfileItem
            label="Affiliation"
            value={profile.affiliation}
          />

          <ProfileItem
            label="Lab / Research Group"
            value={profile.lab_name}
          />

          <ProfileItem
            label="Accepting Students"
            value={
              profile.accepting_students === true
                ? "Yes"
                : profile.accepting_students === false
                ? "No"
                : "Not specified"
            }
          />

          <ProfileItem
            label="Academic Website"
            value={profile.academic_url}
            link
          />

          <ProfileItem
            label="Research Interests"
            value={profile.research_interests}
            wide
          />

          <ProfileItem
            label="Bio"
            value={profile.bio}
            wide
          />
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-2xl border border-line bg-panel p-6"
        >
          {saveError && (
            <p
              role="alert"
              className="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200"
            >
              {saveError}
            </p>
          )}

          <div className="grid gap-5 md:grid-cols-2">
            <Field
              label="Full Name"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              required
            />

            <Field
              label="Email"
              name="email"
              value={form.email}
              disabled
            />

            <Field
              label="Title / Designation"
              name="title"
              value={form.title}
              onChange={handleChange}
              placeholder="e.g. Associate Professor"
            />

            <Field
              label="Department"
              name="department"
              value={form.department}
              onChange={handleChange}
              placeholder="e.g. Computer Science"
            />

            <Field
              label="Affiliation"
              name="affiliation"
              value={form.affiliation}
              onChange={handleChange}
              placeholder="e.g. University at Albany"
            />

            <Field
              label="Lab / Research Group"
              name="lab_name"
              value={form.lab_name}
              onChange={handleChange}
            />

            <div>
              <label
                htmlFor="accepting_students"
                className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/60"
              >
                Accepting Students
              </label>

              <select
                id="accepting_students"
                name="accepting_students"
                value={
                  form.accepting_students === null
                    ? ""
                    : String(
                        form.accepting_students
                      )
                }
                onChange={(event) => {
                  const value =
                    event.target.value;

                  setForm((current) => ({
                    ...current,
                    accepting_students:
                      value === ""
                        ? null
                        : value === "true",
                  }));
                }}
                className="mt-2 w-full rounded-xl border border-line bg-ink/30 px-3 py-2 text-sm text-white outline-none focus:border-sage/50"
              >
                <option value="">
                  Not specified
                </option>
                <option value="true">
                  Yes
                </option>
                <option value="false">
                  No
                </option>
              </select>
            </div>

            <Field
              label="Academic Website"
              name="academic_url"
              value={form.academic_url}
              onChange={handleChange}
              placeholder="https://..."
            />
          </div>

          <TextArea
            label="Research Interests"
            name="research_interests"
            value={form.research_interests}
            onChange={handleChange}
          />

          <TextArea
            label="Bio"
            name="bio"
            value={form.bio}
            onChange={handleChange}
          />

          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-sage px-5 py-2 text-sm font-semibold text-ink hover:bg-sage-light disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving
                ? "Saving…"
                : "Save profile"}
            </button>

            <button
              type="button"
              onClick={cancelEditing}
              disabled={saving}
              className="rounded-lg border border-line px-5 py-2 text-sm font-semibold text-mist hover:border-sage/40 hover:text-white disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}


function ProfileItem({
  label,
  value,
  wide = false,
  link = false,
}) {
  return (
    <div
      className={`rounded-2xl border border-line bg-panel p-5 ${
        wide ? "md:col-span-2" : ""
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/55">
        {label}
      </p>

      {link && value ? (
        <a
          href={value}
          target="_blank"
          rel="noreferrer"
          className="mt-2 block break-words text-sm text-sage hover:text-sage-light"
        >
          {value}
        </a>
      ) : (
        <p className="mt-2 whitespace-pre-wrap text-sm text-mist/85">
          {value || "Not provided"}
        </p>
      )}
    </div>
  );
}


function Field({
  label,
  name,
  value,
  onChange,
  required = false,
  disabled = false,
  placeholder = "",
}) {
  return (
    <div>
      <label
        htmlFor={name}
        className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/60"
      >
        {label}
      </label>

      <input
        id={name}
        name={name}
        type="text"
        value={value || ""}
        onChange={onChange}
        required={required}
        disabled={disabled}
        placeholder={placeholder}
        className="mt-2 w-full rounded-xl border border-line bg-ink/30 px-3 py-2 text-sm text-white outline-none placeholder:text-mist/35 focus:border-sage/50 disabled:cursor-not-allowed disabled:opacity-50"
      />
    </div>
  );
}


function TextArea({
  label,
  name,
  value,
  onChange,
}) {
  return (
    <div>
      <label
        htmlFor={name}
        className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/60"
      >
        {label}
      </label>

      <textarea
        id={name}
        name={name}
        rows={4}
        value={value || ""}
        onChange={onChange}
        className="mt-2 w-full resize-y rounded-xl border border-line bg-ink/30 px-3 py-2 text-sm text-white outline-none focus:border-sage/50"
      />
    </div>
  );
}
