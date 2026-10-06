export type User = { id: number; email: string; admin: boolean };

// Throws the HTTP status as the error message, so callers can tell 401 from 429.
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export function post<T>(path: string, body: object = {}, init?: RequestInit): Promise<T> {
  return api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    ...init,
  });
}
