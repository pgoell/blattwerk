export type User = { id: number; email: string; admin: boolean };

// Throws the HTTP status as the error message, so callers can tell 401 from 429. `by` is the user a sheet's 404 was
// served for, where the server named one.
export type Refusal = Error & { by?: number };
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) throw Object.assign(new Error(String(res.status)), { by: Number(res.headers.get("X-User")) || undefined });
  return res.json();
}

// What the app does when a request finds the session gone, or a sheet served for another account than the window
// holds, and how many times somebody has signed in or out.
let signedOut = () => {};
let other = () => {};
let logins = 0;
export const onSignedOut = (then: () => void) => void (signedOut = then);
export const onOther = (then: () => void) => void (other = then);
export const showLogin = () => signedOut();
export const catchUp = () => other();
export const countLogin = () => void logins++;
// A request that finds the session gone brings the login, on the address as it stands. Not where somebody has
// signed in since it went: that answer is about the session before, and `logins` counts them. It is "stale" then,
// a failure like any other: no saver stops for it, and the next try goes with the new session.
export function signed<T>(asked: Promise<T>) {
  const was = logins;
  return asked.catch((e: Error) => {
    if (e.message === "401" && was !== logins) throw new Error("stale");
    if (e.message === "401") signedOut();
    throw e;
  });
}

export function post<T>(path: string, body: object = {}, init?: RequestInit): Promise<T> {
  return api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    ...init,
  });
}
