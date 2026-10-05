// client.js — THE ONE PLACE THAT TALKS TO THE BACKEND.
// Pages call api("/users/me") instead of writing fetch() themselves.
//
// Examples:
//   Get data:   const me = await api("/users/me");
//   Send data:  await api("/auth/login", { method: "POST", body: JSON.stringify({ ... }) });

// ---------- Saving the login token ----------
// After login, the backend gives us a token. We keep it in the browser's
// localStorage so the user stays logged in even after refreshing the page.
const TOKEN_KEY = "gradtrack_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const saveToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export async function api(path, options = {}) {
  const token = getToken();

  // 1. Add "/api" to the front, so "/users/me" becomes "/api/users/me".
  //    (vite.config.js then forwards anything starting with /api to the backend.)
  const res = await fetch(`/api${path}`, {
    ...options,
    headers: {
      // 2. Tell the backend we are sending JSON data.
      "Content-Type": "application/json",
      // 3. If we are logged in, show our token (the "wristband") on every request.
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  // 4. 401 = our token is missing, fake, or expired → log out and go to the login page.
  //    (Only if we HAD a token — a wrong password on the login page is also 401,
  //    and there we just want to show the error message.)
  if (res.status === 401 && token) {
    clearToken();
    window.location.href = "/login";
  }

  // 5. Any other error: stop and pass the backend's message along
  //    (e.g. "Invalid email or password"), so pages can show it.
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // Form-check errors (422) come as a list, e.g. [{ msg: "...at least 8 characters" }].
    // Join them into one readable sentence.
    const message = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg.replace(/^Value error, /, "")).join(". ")
      : body.detail;
    throw new Error(message || `Request failed (${res.status})`);
  }

  // 6. Turn the backend's JSON reply into a normal JavaScript object/array.
  return res.json();
}
