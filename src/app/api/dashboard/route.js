const PYTHON_BACKEND_URL =
  process.env.PYTHON_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

function getSessionHeaders(request) {
  const sessionId = request.headers.get("X-Session-Id");
  const sessionToken = request.headers.get("X-Session-Token");

  const headers = {
    "Content-Type": "application/json",
  };

  if (sessionId) {
    headers["X-Session-Id"] = sessionId;
  }

  if (sessionToken) {
    headers["X-Session-Token"] = sessionToken;
  }

  return headers;
}

export async function GET(request) {
  try {
    const response = await fetch(`${PYTHON_BACKEND_URL}/dashboard-stats`, {
      method: "GET",
      headers: getSessionHeaders(request),
      cache: "no-store",
    });

    const data = await response.json();

    return Response.json(data, {
      status: response.status,
    });
  } catch (error) {
    return Response.json(
      {
        error: "Dashboard API request failed.",
        details: error.message,
      },
      {
        status: 500,
      }
    );
  }
}