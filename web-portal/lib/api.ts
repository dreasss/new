export const API = process.env.NEXT_PUBLIC_CORE_API_URL;

export function tokenHeader(): HeadersInit {
  const token = typeof window === "undefined" ? null : localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiGet(path: string) {
  return fetch(`${API}${path}`, { headers: { ...tokenHeader() } });
}

export async function apiPost(path: string, body: unknown, extraHeaders?: HeadersInit) {
  return fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...tokenHeader(), ...extraHeaders },
    body: JSON.stringify(body),
  });
}
