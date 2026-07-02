const PYTHON_BACKEND_URL =
  process.env.PYTHON_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

export async function POST(request) {
  try {
    const body = await request.json();

    const {
      action,
      domain,
      topic,
      difficulty,
      challenge,
      submission,
    } = body;

    if (action === "generate") {
      const response = await fetch(
        `${PYTHON_BACKEND_URL}/generate-project-challenge`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            domain,
            topic,
            difficulty,
          }),
        }
      );

      const data = await response.json();

      return Response.json(data);
    }

    if (action === "evaluate") {
      const response = await fetch(
        `${PYTHON_BACKEND_URL}/evaluate-project-submission`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            domain,
            topic,
            difficulty,
            challenge,
            submission,
          }),
        }
      );

      const data = await response.json();

      return Response.json(data);
    }

    return Response.json(
      {
        error: "Invalid project action",
      },
      {
        status: 400,
      }
    );
  } catch (error) {
    return Response.json(
      {
        error: "Next.js project API failed while connecting to Python backend.",
        details: error.message,
      },
      {
        status: 500,
      }
    );
  }
}