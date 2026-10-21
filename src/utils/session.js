const SESSION_ID_KEY = "conceptviva_session_id";
const SESSION_TOKEN_KEY = "conceptviva_session_token";
const SESSION_EXPIRES_AT_KEY = "conceptviva_session_expires_at";

// if multiple components call ensureConceptVivaSession() at the same time
// (e.g. the dashboard firing two fetches in parallel), we don't want each
// one to independently create a brand new session. This holds the
// in-flight session-creation promise so everyone waits on the same one.
let pendingSessionPromise = null;

function getCurrentTimeMs() {
  return Date.now();
}

function isExpired(expiresAt) {
  if (!expiresAt) {
    return false;
  }

  const expiryTime = Number(expiresAt);

  if (!expiryTime || Number.isNaN(expiryTime)) {
    return false;
  }

  const safetyBufferMs = 60 * 1000;

  return getCurrentTimeMs() + safetyBufferMs >= expiryTime;
}

function normalizeHeaders(headers = {}) {
  if (headers instanceof Headers) {
    return Object.fromEntries(headers.entries());
  }

  return { ...headers };
}

function shouldRetryWithFreshSession(status) {
  return status === 401 || status === 403;
}

export function getStoredSession() {
  if (typeof window === "undefined") {
    return {
      sessionId: "",
      sessionToken: "",
      expiresAt: "",
    };
  }

  return {
    sessionId: localStorage.getItem(SESSION_ID_KEY) || "",
    sessionToken: localStorage.getItem(SESSION_TOKEN_KEY) || "",
    expiresAt: localStorage.getItem(SESSION_EXPIRES_AT_KEY) || "",
  };
}

export function saveSession(sessionId, sessionToken, expiresInSeconds = 2592000) {
  if (typeof window === "undefined") return;

  const expiresAt = getCurrentTimeMs() + Number(expiresInSeconds) * 1000;

  localStorage.setItem(SESSION_ID_KEY, sessionId);
  localStorage.setItem(SESSION_TOKEN_KEY, sessionToken);
  localStorage.setItem(SESSION_EXPIRES_AT_KEY, String(expiresAt));
}

export function clearSession() {
  if (typeof window === "undefined") return;

  localStorage.removeItem(SESSION_ID_KEY);
  localStorage.removeItem(SESSION_TOKEN_KEY);
  localStorage.removeItem(SESSION_EXPIRES_AT_KEY);
}

async function createNewSession() {
  const response = await fetch("/api/session", {
    method: "POST",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to create ConceptVivaAI session.");
  }

  const data = await response.json();

  if (!data.session_id || !data.session_token) {
    throw new Error("Invalid session response from backend.");
  }

  saveSession(
    data.session_id,
    data.session_token,
    data.expires_in_seconds || 2592000
  );

  return {
    sessionId: data.session_id,
    sessionToken: data.session_token,
  };
}

// wraps createNewSession so that parallel callers share one request
// instead of each firing off their own "/api/session" call
async function createNewSessionShared() {
  if (pendingSessionPromise) {
    return pendingSessionPromise;
  }

  pendingSessionPromise = createNewSession().finally(() => {
    pendingSessionPromise = null;
  });

  return pendingSessionPromise;
}

export async function forceNewConceptVivaSession() {
  clearSession();
  return createNewSessionShared();
}

export async function ensureConceptVivaSession() {
  const stored = getStoredSession();

  if (
    stored.sessionId &&
    stored.sessionToken &&
    !isExpired(stored.expiresAt)
  ) {
    return {
      sessionId: stored.sessionId,
      sessionToken: stored.sessionToken,
    };
  }

  clearSession();
  return createNewSessionShared();
}

// Signed-in users authenticate with an HttpOnly cookie. The backend additionally
// requires this readable CSRF cookie to be echoed in a header on unsafe requests.
export function getCsrfToken() {
  if (typeof document === "undefined") return "";

  const match = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("cv_csrf="));

  return match ? decodeURIComponent(match.slice("cv_csrf=".length)) : "";
}

export async function getSessionHeaders() {
  const session = await ensureConceptVivaSession();
  const headers = {
    "X-Session-Id": session.sessionId,
    "X-Session-Token": session.sessionToken,
  };

  const csrf = getCsrfToken();
  if (csrf) {
    headers["X-CSRF-Token"] = csrf;
  }

  return headers;
}

export async function apiFetchWithSessionRetry(url, options = {}) {
  const originalHeaders = normalizeHeaders(options.headers);
  const sessionHeaders = await getSessionHeaders();

  const firstResponse = await fetch(url, {
    ...options,
    headers: {
      ...originalHeaders,
      ...sessionHeaders,
    },
    cache: options.cache || "no-store",
  });

  if (!shouldRetryWithFreshSession(firstResponse.status)) {
    return firstResponse;
  }

  // A 403 caused by a CSRF/Origin problem is not fixed by a new guest session.
  if (getCsrfToken() && firstResponse.status === 403) {
    return firstResponse;
  }

  const freshSession = await forceNewConceptVivaSession();
  const csrf = getCsrfToken();

  return fetch(url, {
    ...options,
    headers: {
      ...originalHeaders,
      "X-Session-Id": freshSession.sessionId,
      "X-Session-Token": freshSession.sessionToken,
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    cache: options.cache || "no-store",
  });
}

export async function logoutConceptVivaSession() {
  const stored = getStoredSession();

  if (!stored.sessionId || !stored.sessionToken) {
    clearSession();
    return {
      loggedOut: true,
      message: "No active session found.",
    };
  }

  try {
    const response = await fetch("/api/session/logout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Id": stored.sessionId,
        "X-Session-Token": stored.sessionToken,
      },
      cache: "no-store",
    });

    let data = {};

    try {
      data = await response.json();
    } catch {
      data = {};
    }

    clearSession();

    return {
      loggedOut: response.ok,
      status: response.status,
      ...data,
    };
  } catch (error) {
    clearSession();

    return {
      loggedOut: false,
      message: "Local session cleared, but backend logout request failed.",
      details: error.message,
    };
  }
}