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
    const { searchParams } = new URL(request.url);
    const endpoint =
      searchParams.get("resource") === "bank-stats"
        ? "/dsa-question-bank/stats"
        : "/dsa-question-bank";

    const response = await fetch(`${PYTHON_BACKEND_URL}${endpoint}`, {
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
        error: "DSA API request failed.",
        details: error.message,
      },
      {
        status: 500,
      }
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();

    let endpoint = "/generate-dsa-problem";

    if (body.action === "generate") {
      endpoint = "/generate-dsa-problem";
    }

    if (body.action === "generateMockSet") {
      endpoint = "/generate-dsa-mock-set";
    }

    if (body.action === "generateFromQuestion") {
      endpoint = "/generate-own-dsa-question";
    }

    if (body.action === "generateAI") {
      endpoint = "/generate-ai-practice-question";
    }

    if (body.action === "evaluate") {
      endpoint = "/evaluate-dsa-solution";
    }

    if (body.action === "save") {
      endpoint = "/save-dsa-attempt";
    }

    if (body.action === "translateHindi") {
      endpoint = "/translate-to-hindi";
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
        error: "DSA API request failed.",
        details: error.message,
      },
      {
        status: 500,
      }
    );
  }
}