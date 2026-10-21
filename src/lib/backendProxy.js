// Server-only helper used by every /api route handler to call the FastAPI backend.
//
// The browser only ever talks to this Next.js origin, so the backend's auth cookies
// are first-party. We forward just what the backend needs (guest session headers,
// CSRF token, our own cv_* cookies, request id, origin) and relay status, body,
// Set-Cookie, redirects and rate-limit headers back unchanged.

const BACKEND_URL =
  process.env.PYTHON_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

const FORWARDED_REQUEST_HEADERS = [
  "content-type",
  "x-session-id",
  "x-session-token",
  "x-csrf-token",
  "x-request-id",
  "origin",
];

const RELAYED_RESPONSE_HEADERS = ["content-type", "retry-after", "x-request-id", "location"];

function backendCookies(cookieHeader) {
  if (!cookieHeader) return "";
  return cookieHeader
    .split(";")
    .map((part) => part.trim())
    .filter((part) => part.startsWith("cv_"))
    .join("; ");
}

function forwardedHeaders(request) {
  const headers = new Headers();

  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  if (!headers.has("content-type") && !["GET", "HEAD"].includes(request.method)) {
    headers.set("content-type", "application/json");
  }

  const cookies = backendCookies(request.headers.get("cookie"));
  if (cookies) headers.set("cookie", cookies);

  // The backend only trusts this when TRUSTED_PROXY_HOPS is configured for it.
  const clientIp = (request.headers.get("x-forwarded-for") || "").split(",")[0].trim();
  if (clientIp) headers.set("x-forwarded-for", clientIp);

  return headers;
}

export async function proxyToBackend(request, path, { method = request.method, body } = {}) {
  let response;

  try {
    response = await fetch(`${BACKEND_URL}${path}`, {
      method,
      headers: forwardedHeaders(request),
      body,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json(
      {
        error: "Backend unavailable.",
        detail: "The API server could not be reached. Please try again shortly.",
      },
      { status: 502 }
    );
  }

  const headers = new Headers();
  for (const name of RELAYED_RESPONSE_HEADERS) {
    const value = response.headers.get(name);
    if (value) headers.set(name, value);
  }
  for (const cookie of response.headers.getSetCookie?.() ?? []) {
    headers.append("set-cookie", cookie);
  }

  const payload = [204, 304].includes(response.status) ? null : await response.arrayBuffer();
  return new Response(payload, { status: response.status, headers });
}

// For the legacy "action" style routes: { action: "evaluate", ...payload }.
export async function proxyAction(request, actions, defaultAction) {
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const action = body?.action || defaultAction;
  const path = actions[action];
  if (!path) {
    return Response.json({ error: `Unknown action "${action}".` }, { status: 400 });
  }

  const payload = { ...body };
  delete payload.action;
  return proxyToBackend(request, path, { method: "POST", body: JSON.stringify(payload) });
}
