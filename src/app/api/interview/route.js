const PYTHON_BACKEND_URL =
  process.env.PYTHON_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

export async function POST(request) {
  try {
    const body = await request.json();

    const { action, topic, level, question, answer } = body;

    if (action === "question") {
      const response = await fetch(`${PYTHON_BACKEND_URL}/generate-question`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic,
          level,
        }),
      });

      const data = await response.json();

      return Response.json({
        question: data.question || "Question generation failed.",
      });
    }

    if (action === "evaluate") {
      const response = await fetch(`${PYTHON_BACKEND_URL}/evaluate-answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic,
          level,
          question,
          answer,
        }),
      });

      const data = await response.json();

      return Response.json(data);
    }

    return Response.json(
      {
        error: "Invalid action",
      },
      {
        status: 400,
      }
    );
  } catch (error) {
    return Response.json(
      {
        error: "Next.js API failed while connecting to Python backend.",
        details: error.message,
      },
      {
        status: 500,
      }
    );
  }
} 