export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export class SessionChanged extends Error {}

const publicWebsite = "https://pharma-path.onrender.com";
const publicApi = "https://grd-supply-demo.onrender.com";

function apiOrigins(origin: string) {
  // Both HTTPS names reach the same API and SQL ledger. Keep origin stable for
  // account-bound cache/outbox keys, but bypass the website proxy on native apps.
  // Custom organisation servers must never send credentials to this public API.
  return origin === publicWebsite || origin === publicApi
    ? [publicApi, publicWebsite]
    : [origin];
}

function dnsFailure(error: unknown) {
  return (
    error instanceof Error &&
    /UnknownHostException|Unable to resolve host|No address associated with hostname|ENOTFOUND|EAI_AGAIN/i.test(
      error.message,
    )
  );
}

function connectionFailure(error: unknown) {
  return (
    error instanceof TypeError ||
    dnsFailure(error) ||
    (error instanceof Error &&
      /Network request failed|fetch failed|Failed to fetch|NetworkError|ConnectException|Failed to connect|SocketException|SocketTimeoutException/i.test(
        error.message,
      ))
  );
}

export function serverOrigin(value: string) {
  const url = new URL(value.trim());
  const h = url.hostname;
  const local =
    h === "localhost" ||
    h === "127.0.0.1" ||
    h === "10.0.2.2" ||
    /^10\.\d+\.\d+\.\d+$/.test(h) ||
    /^192\.168\.\d+\.\d+$/.test(h) ||
    /^172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$/.test(h);
  if (
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    !["", "/"].includes(url.pathname)
  )
    throw new Error(
      "Enter only the server origin, such as https://grd.example.com.",
    );
  if (url.protocol !== "https:" && !(url.protocol === "http:" && local))
    throw new Error(
      "Use HTTPS for hosted servers. HTTP is allowed only for local development.",
    );
  return url.origin;
}

export class Transport {
  private epoch = 0;
  private token: string | null = null;
  private connectedOrigin: string | null = null;
  constructor(
    public origin: string,
    private expired: () => void = () => {},
  ) {}
  authenticate(token: string | null) {
    this.epoch++;
    this.token = token;
  }
  async request<T>(
    path: string,
    method = "GET",
    body?: unknown,
    key?: string,
  ): Promise<T> {
    const epoch = this.epoch;
    const controller = new AbortController();
    // A free demo host can need about a minute to wake after inactivity.
    const timer = setTimeout(() => controller.abort(), 90000);
    try {
      const options: RequestInit = {
        method,
        signal: controller.signal,
        headers: {
          ...(this.token ? { Authorization: "Bearer " + this.token } : {}),
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
          ...(key ? { "Idempotency-Key": key } : {}),
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      };
      const configured = apiOrigins(this.origin);
      const origins = this.connectedOrigin
        ? [
            this.connectedOrigin,
            ...configured.filter((o) => o !== this.connectedOrigin),
          ]
        : configured;
      let response: Response | undefined;
      for (let index = 0; index < origins.length; index++) {
        if (epoch !== this.epoch) throw new SessionChanged();
        try {
          response = await fetch(origins[index] + "/api/v1" + path, options);
          if (epoch !== this.epoch) throw new SessionChanged();
          this.connectedOrigin = origins[index];
          break;
        } catch (error) {
          if (epoch !== this.epoch) throw new SessionChanged();
          // A lost reply may already have committed a write. Only replay reads,
          // persisted idempotent commands, or a confirmed DNS lookup failure.
          const safeToRepeat =
            ["GET", "HEAD"].includes(method.toUpperCase()) ||
            Boolean(key) ||
            dnsFailure(error);
          if (
            index === origins.length - 1 ||
            controller.signal.aborted ||
            !connectionFailure(error) ||
            !safeToRepeat
          )
            throw error;
        }
      }
      if (!response) throw new Error("No server response.");
      if (epoch !== this.epoch) throw new SessionChanged();
      let result: { detail?: unknown };
      try {
        result = await response.json();
      } catch {
        if (epoch !== this.epoch) throw new SessionChanged();
        throw new ApiError(
          502,
          "Response unreadable. Keep the original command and retry to confirm its result.",
        );
      }
      if (epoch !== this.epoch) throw new SessionChanged();
      if (!response.ok) {
        if (response.status === 401) {
          this.authenticate(null);
          this.expired();
        }
        throw new ApiError(
          response.status,
          typeof result.detail === "string"
            ? result.detail
            : "Check the entered values and your access.",
        );
      }
      return result as T;
    } catch (error) {
      if (
        epoch !== this.epoch &&
        !(error instanceof ApiError && error.status === 401)
      )
        throw new SessionChanged();
      if (error instanceof Error && error.name === "AbortError")
        throw new Error(
          "The server did not respond in time. Check the connection and retry the saved action to confirm its result.",
        );
      if (connectionFailure(error))
        throw new Error(
          "Cannot connect to Pharma Path. Try mobile data or another Wi-Fi network, then retry. Saved actions remain on this phone.",
        );
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }
  async all<T>(path: string): Promise<T[]> {
    const items: T[] = [];
    for (let offset = 0; offset < 20000; offset += 200) {
      const page = await this.request<{ items: T[]; total: number }>(
        `${path}${path.includes("?") ? "&" : "?"}offset=${offset}&limit=200`,
      );
      items.push(...page.items);
      if (items.length >= page.total) return items;
    }
    throw new Error("Too many records. Narrow your access scope.");
  }
}
