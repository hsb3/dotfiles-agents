export type Fetcher = typeof fetch;
export type ApiResult<T> =
  | { kind: "ok"; data: T }
  | { kind: "access"; status: 401 | 403 }
  | { kind: "error"; status: number; message: string };
export type AdapterOptions = RequestInit & { token?: string; fetcher?: Fetcher };
type Timer = ReturnType<typeof setTimeout>;
type Clock = { now(): number; setTimeout(callback: () => void, delay: number): Timer; clearTimeout(timer: Timer): void };
const systemClock: Clock = { now: Date.now, setTimeout, clearTimeout };

function jwtExpiry(token: string): number | undefined {
  try {
    const payload = token.split(".")[1];
    if (!payload) return undefined;
    const json = atob(payload.replaceAll("-", "+").replaceAll("_", "/").padEnd(Math.ceil(payload.length / 4) * 4, "="));
    const exp = JSON.parse(json).exp;
    return typeof exp === "number" && Number.isFinite(exp) ? exp * 1_000 : undefined;
  } catch {
    return undefined;
  }
}

export async function request<T>(path: string, options: AdapterOptions = {}): Promise<ApiResult<T>> {
  const { token, fetcher = fetch, headers: supplied, ...init } = options;
  const headers = new Headers(supplied);
  if (token) headers.set("Authorization", token);
  try {
    const response = await fetcher(path, { ...init, headers });
    if (response.status === 401 || response.status === 403) return { kind: "access", status: response.status };
    if (!response.ok) return { kind: "error", status: response.status, message: await response.text() };
    return { kind: "ok", data: response.status === 204 ? (undefined as T) : await response.json() as T };
  } catch (error) {
    return { kind: "error", status: 0, message: error instanceof Error ? error.message : "Request failed" };
  }
}

type Auth = { token: string };
const AUTH_PATH = "/api/collections/users/auth-with-password";

export function login(email: string, password: string, fetcher: Fetcher = fetch) {
  return request<Auth>(AUTH_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identity: email, password }),
    fetcher,
  });
}

export type PrivateState = { selections: Record<string, string[]>; loaded: Record<string, unknown> };

export class Session {
  #token = "";
  #generation = 0;
  #controllers = new Set<AbortController>();
  #selections: Record<string, string[]> = {};
  #loaded: Record<string, unknown> = {};
  #expiryTimer?: Timer;

  constructor(readonly fetcher: Fetcher = fetch, readonly clock: Clock = systemClock) {}
  get token() { return this.#token; }
  get generation() { return this.#generation; }
  snapshot(): PrivateState { return { selections: { ...this.#selections }, loaded: { ...this.#loaded } }; }
  setSelection(key: string, value: string[]) { this.#selections[key] = [...value]; }
  setLoaded(key: string, value: unknown) { this.#loaded[key] = value; }

  #clear() {
    if (this.#expiryTimer !== undefined) this.clock.clearTimeout(this.#expiryTimer);
    this.#expiryTimer = undefined;
    this.#generation += 1;
    this.#controllers.forEach((controller) => controller.abort());
    this.#controllers.clear();
    this.#token = "";
    this.#selections = {};
    this.#loaded = {};
  }

  #armExpiry(token: string, generation: number) {
    const expiry = jwtExpiry(token);
    if (expiry === undefined) return;
    const delay = expiry - this.clock.now();
    if (delay <= 0) return this.#clear();
    this.#expiryTimer = this.clock.setTimeout(() => {
      if (generation === this.#generation) this.#clear();
    }, delay);
  }

  logout() { this.#clear(); }

  async login(email: string, password: string) {
    this.#clear();
    const generation = this.#generation;
    const result = await login(email, password, this.fetcher);
    if (generation !== this.#generation) return { kind: "error", status: 0, message: "Session changed" } as const;
    if (result.kind === "ok" && result.data.token) {
      this.#token = result.data.token;
      this.#armExpiry(result.data.token, generation);
    }
    return result;
  }

  async request<T>(path: string, options: Omit<AdapterOptions, "token" | "fetcher"> = {}) {
    const generation = this.#generation;
    const controller = new AbortController();
    const cancel = () => controller.abort();
    options.signal?.addEventListener("abort", cancel, { once: true });
    if (options.signal?.aborted) cancel();
    this.#controllers.add(controller);
    const result = await request<T>(path, { ...options, signal: controller.signal, token: this.#token, fetcher: this.fetcher });
    options.signal?.removeEventListener("abort", cancel);
    this.#controllers.delete(controller);
    if (generation !== this.#generation || controller.signal.aborted)
      return { kind: "error", status: 0, message: "Request cancelled" } as const;
    if (result.kind === "access" && result.status === 401) {
      this.#clear();
      return result;
    }
    return result;
  }

  async load<T>(key: string, loader: (token: string, signal: AbortSignal) => Promise<T>) {
    const generation = this.#generation;
    const controller = new AbortController();
    this.#controllers.add(controller);
    try {
      const value = await loader(this.#token, controller.signal);
      if (generation !== this.#generation) return undefined;
      this.#loaded[key] = value;
      return value;
    } finally {
      this.#controllers.delete(controller);
    }
  }
}

export async function protectedFileToken(session: Session): Promise<{ kind: "ok"; token: string } | Exclude<ApiResult<unknown>, { kind: "ok" }>> {
  const result = await session.request<{ token?: string }>("/api/files/token", { method: "POST" });
  if (result.kind !== "ok") return result;
  return typeof result.data.token === "string" && result.data.token.trim()
    ? { kind: "ok", token: result.data.token }
    : { kind: "error", status: 0, message: "File token missing" };
}
