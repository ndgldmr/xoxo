const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export function getApiKey(): string {
  return sessionStorage.getItem("xoxo_api_key") ?? ""
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const key = getApiKey()
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(key ? { "X-API-Key": key } : {}),
      ...(init.headers ?? {}),
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status} ${text}`)
  }
  // 204 No Content
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
