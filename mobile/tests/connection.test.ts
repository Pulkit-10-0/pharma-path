import { strict as assert } from "node:assert";
import { test } from "node:test";
import { ApiError, SessionChanged, Transport } from "../src/transport";

const website = "https://pharma-path.onrender.com";
const backend = "https://grd-supply-demo.onrender.com";
const dns = () =>
  new Error(
    'fetch failed: java.net.UnknownHostException: Unable to resolve host "grd-supply-demo.onrender.com": No address associated with hostname',
  );
const ok = (value: unknown = { ok: true }) =>
  new Response(JSON.stringify(value));

test("existing branded server settings use the direct HTTPS API without changing cache identity", async () => {
  const previous = globalThis.fetch;
  const calls: string[] = [];
  globalThis.fetch = async (url) => {
    calls.push(String(url));
    return ok();
  };
  try {
    const api = new Transport(website);
    await api.request("/me");
    assert.deepEqual(calls, [backend + "/api/v1/me"]);
    assert.equal(api.origin, website);
  } finally {
    globalThis.fetch = previous;
  }
});

test("Android DNS failure can fall back on login, then reuse the reachable HTTPS host", async () => {
  const previous = globalThis.fetch;
  const calls: { url: string; options?: RequestInit }[] = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    if (String(url).startsWith(backend)) throw dns();
    return ok();
  };
  try {
    const api = new Transport(website);
    await api.request("/auth/login", "POST", {
      email: "test",
      password: "test",
    });
    api.authenticate("token");
    await api.request("/me");
    assert.deepEqual(
      calls.map((c) => c.url),
      [
        backend + "/api/v1/auth/login",
        website + "/api/v1/auth/login",
        website + "/api/v1/me",
      ],
    );
    assert.equal(calls[0].options?.body, calls[1].options?.body);
  } finally {
    globalThis.fetch = previous;
  }
});

test("lost stock-command reply retries the exact persisted body and idempotency key", async () => {
  const previous = globalThis.fetch;
  const calls: { url: string; options?: RequestInit }[] = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    if (calls.length === 1) throw new TypeError("Network request failed");
    return ok({ id: "recorded-once" });
  };
  try {
    const api = new Transport(website);
    api.authenticate("original-token");
    const result = await api.request(
      "/shipments/a/receipts",
      "POST",
      { accepted: 20 },
      "saved-key",
    );
    assert.deepEqual(result, { id: "recorded-once" });
    assert.equal(calls.length, 2);
    assert.equal(calls[0].options?.body, calls[1].options?.body);
    assert.deepEqual(calls[0].options?.headers, calls[1].options?.headers);
    assert.equal(
      (calls[1].options?.headers as Record<string, string>)["Idempotency-Key"],
      "saved-key",
    );
  } finally {
    globalThis.fetch = previous;
  }
});

test("an ambiguous failed write without an idempotency key is not replayed", async () => {
  const previous = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    throw new TypeError("Network request failed");
  };
  try {
    await assert.rejects(
      new Transport(website).request("/auth/login", "POST", { email: "test" }),
      /Cannot connect to Pharma Path/,
    );
    assert.equal(calls, 1);
  } finally {
    globalThis.fetch = previous;
  }
});

test("unreachable names show a useful message rather than a native Java exception", async () => {
  const previous = globalThis.fetch;
  const calls: string[] = [];
  globalThis.fetch = async (url) => {
    calls.push(String(url));
    throw dns();
  };
  try {
    await assert.rejects(
      new Transport(website).request("/me"),
      (error: Error) => {
        assert.match(error.message, /mobile data or another Wi-Fi/);
        assert.doesNotMatch(error.message, /java\.net|UnknownHostException/);
        return true;
      },
    );
    assert.equal(calls.length, 2);
  } finally {
    globalThis.fetch = previous;
  }
});

test("custom organisation servers never fall back or send credentials to public hosts", async () => {
  const previous = globalThis.fetch;
  const calls: string[] = [];
  globalThis.fetch = async (url) => {
    calls.push(String(url));
    throw dns();
  };
  try {
    const api = new Transport("https://private.example.com");
    api.authenticate("company-token");
    await assert.rejects(api.request("/me"), /Cannot connect/);
    assert.deepEqual(calls, ["https://private.example.com/api/v1/me"]);
  } finally {
    globalThis.fetch = previous;
  }
});

test("HTTP access and stock conflicts do not trigger an alternate-host replay", async () => {
  const previous = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response(JSON.stringify({ detail: "Stock version changed" }), {
      status: 409,
    });
  };
  try {
    await assert.rejects(
      new Transport(website).request("/plans/a/approve", "POST", {}, "key"),
      ApiError,
    );
    assert.equal(calls, 1);
  } finally {
    globalThis.fetch = previous;
  }
});

test("a signed-out request cannot retry on the alternate host with the previous token", async () => {
  const previous = globalThis.fetch;
  let reject!: (error: Error) => void;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Promise<Response>((_resolve, fail) => {
      reject = fail;
    });
  };
  try {
    const api = new Transport(website);
    api.authenticate("old-token");
    const pending = api.request("/me");
    api.authenticate(null);
    reject(dns());
    await assert.rejects(pending, SessionChanged);
    assert.equal(calls, 1);
  } finally {
    globalThis.fetch = previous;
  }
});

test("request timeouts stop failover and retain the original retry guidance", async () => {
  const previous = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    throw new DOMException("Aborted", "AbortError");
  };
  try {
    await assert.rejects(
      new Transport(website).request("/me"),
      /did not respond in time/,
    );
    assert.equal(calls, 1);
  } finally {
    globalThis.fetch = previous;
  }
});
