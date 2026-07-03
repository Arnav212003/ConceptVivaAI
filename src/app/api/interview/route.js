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

export async function POST(request) {
  try {
    const body = await request.json();

    let endpoint = "/generate-question";

    if (body.action === "question") {
      endpoint = "/generate-question";
    }

    if (body.action === "evaluate") {
      endpoint = "/evaluate-answer";
    }

    if (body.action === "save") {
      endpoint = "/save-ml-practice-attempt";
    }

    if (body.action === "saveInterviewReport") {
      endpoint = "/save-interview-report";
    }

    const payload = { ...body };
    delete payload.action;

    const response = await fetch(`${PYTHON_BACKEND_URL}${endpoint}`, {
      method: "POST",
      headers: getSessionHeaders(request),
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const data = await response.json();

    return Response.json(data, {
      status: response.status,
    });
  } catch (error) {
    return Response.json(
      {
        error: "Interview API request failed.",
        details: error.message,
      },
      {
        status: 500,
      }
    );
  }
}