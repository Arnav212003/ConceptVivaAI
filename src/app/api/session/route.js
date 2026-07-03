const PYTHON_BACKEND_URL =
  process.env.PYTHON_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

export async function POST() {
  try {
    const response = await fetch(`${PYTHON_BACKEND_URL}/session/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    const data = await response.json();

    return Response.json(data, {
      status: response.status,
    });
  } catch (error) {
    return Response.json(
      {
        error: "Failed to start ConceptVivaAI session.",
        details: error.message,
      },
      {
        status: 500,
      }
    );
  }
}