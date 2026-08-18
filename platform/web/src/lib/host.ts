// Host API client (packages/services/host_api): the machine-level control
// plane next to the bus — which cells this host can run and which one is
// active. Everything about the running cell stays on zenoh; this is HTTP.
// Base URL: VITE_HOST_API, else the page's host on port 8080.

export interface HostCell {
  id: string;
  name: string;
  cell_type: string | null;
  path: string;
  programs: string | null;
  runtimes: string[];
  error: string | null;
}

export interface HostCells {
  cells: HostCell[];
  active: { cell: string; runtime: string | null; since?: number } | null;
  alive: boolean;
}

export function hostApiBase(): string {
  const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env?.VITE_HOST_API;
  if (env) return env.replace(/\/$/, "");
  const port = (import.meta as unknown as { env?: Record<string, string | undefined> }).env?.VITE_HOST_API_PORT ?? "8080";
  return `${window.location.protocol}//${window.location.hostname}:${port}`;
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${hostApiBase()}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = ((await res.json()) as { detail?: string }).detail ?? detail;
    } catch {
      // keep statusText
    }
    throw new Error(`host api ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export const fetchCells = () => call<HostCells>("GET", "/cells");
export const activateCell = (id: string, runtime: string | null) =>
  call<HostCells>("POST", `/cells/${encodeURIComponent(id)}/activate`, { runtime });
export const stopCell = () => call<HostCells>("POST", "/cells/stop");
