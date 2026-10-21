import { apiFetchWithSessionRetry } from "@/utils/session";

export class ApiError extends Error {
  constructor(message, { status = 0, retryAfter = null, data = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfter = retryAfter;
    this.data = data;
  }
}

function messageFor(status, data, retryAfter) {
  if (status === 429) {
    return `You're going a bit fast. Try again in about ${retryAfter || 60} seconds.`;
  }
  const detail = data?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) return "Some fields are missing or too long. Check your input and try again.";
  if (typeof data?.error === "string") return data.detail || data.error;
  if (status >= 500) return "The server had a problem. Please try again in a moment.";
  return "Request failed. Please try again.";
}

async function request(url, options) {
  let response;
  try {
    response = await apiFetchWithSessionRetry(url, options);
  } catch {
    throw new ApiError("Could not reach ConceptVivaAI. Check your connection and try again.");
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const retryAfter = Number(response.headers?.get?.("Retry-After")) || null;
    throw new ApiError(messageFor(response.status, data, retryAfter), {
      status: response.status,
      retryAfter,
      data,
    });
  }

  return data ?? {};
}

export function apiPost(url, payload) {
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function apiGet(url) {
  return request(url, { method: "GET" });
}
