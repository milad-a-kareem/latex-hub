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
  const headers = {
    'Content-Type': 'application/json',
    ...(await authHeader()),
    ...(init.headers ?? {}),
  };
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export function wsUrl(path: string): string {
  const base = WS_BASE.replace(/^http/, 'ws');
  return `${base}${path}`;
}
