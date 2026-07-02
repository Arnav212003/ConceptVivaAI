const PYTHON_BACKEND_URL = "http://127.0.0.1:8000";

export async function POST(request) {
  try {
    const body = await request.json();

    const { action, topic, difficulty, problem, solution } = body;

    if (action === "generate") {
      const response = await fetch(`${PYTHON_BACKEND_URL}/generate-dsa-problem`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic,
          difficulty,
        }),
      });

      const data = await response.json();

      return Response.json({
        problem: data.problem || "DSA problem generation failed.",
      });
    }

    if (action === "evaluate") {
      const response = await fetch(`${PYTHON_BACKEND_URL}/evaluate-dsa-solution`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic,
          difficulty,
          problem,
          solution,
        }),
      });

      const data = await response.json();

      return Response.json(data);
    }

    return Response.json(
      {
        error: "Invalid DSA action",
      },
      {
        status: 400,
      }
    );
  } catch (error) {
    return Response.json(
      {
        error: "Next.js DSA API failed while connecting to Python backend.",
        details: error.message,
      },
      {
        status: 500,
      }
    );
  }
}