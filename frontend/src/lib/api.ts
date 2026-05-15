import { auth } from './firebase';

const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');
// Firebase Hosting cannot proxy WebSocket upgrades to Cloud Run, so the WS
// client must talk to the Cloud Run domain directly. The deploy workflow
// resolves the service URL via `gcloud run services describe` and injects
// it as VITE_WS_URL. Falls back to BASE for local dev (Vite proxies /ws).
const WS_BASE = ((import.meta.env.VITE_WS_URL as string | undefined) ?? BASE).replace(/\/$/, '');

async function authHeader(): Promise<Record<string, string>> {
  const u = auth.currentUser;
  if (!u) return {};
  const token = await u.getIdToken();
  return { Authorization: `Bearer ${token}` };
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiRaw(path, init, { json: true });
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function apiVoid(path: string, init: RequestInit = {}): Promise<void> {
  await apiRaw(path, init, { json: true });
}

/**
 * Fetch wrapper that auto-injects auth. Unlike `api<T>()`, the caller
 * controls Content-Type (needed for binary uploads). Throws on non-2xx.
 */
export async function apiRaw(
  path: string,
  init: RequestInit = {},
  opts: { json?: boolean } = {},
): Promise<Response> {
  const headers: Record<string, string> = {
    ...(await authHeader()),
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (opts.json && !headers['Content-Type'] && init.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = '';
    try {
      detail = await res.text();
    } catch {
      // ignore
    }
    throw new Error(`${res.status} ${res.statusText}${detail ? `: ${detail}` : ''}`);
  }
  return res;
}

export function wsUrl(path: string): string {
  const base = WS_BASE.replace(/^http/, 'ws');
  return `${base}${path}`;
}
