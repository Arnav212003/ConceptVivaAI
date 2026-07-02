const PYTHON_BACKEND_URL =
  process.env.PYTHON_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

function getDefaultStarterCode() {
  return `class Solution:
    def solve(self):
        # Write your code here
        pass`;
}

function extractStarterCode(problemText = "") {
  const marker = "Starter Code:";
  const index = problemText.indexOf(marker);

  if (index === -1) {
    return getDefaultStarterCode();
  }

  const starterCode = problemText.slice(index + marker.length).trim();

  return starterCode || getDefaultStarterCode();
}

async function callBackend(endpoint, payload) {
  const response = await fetch(`${PYTHON_BACKEND_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Backend request failed: ${endpoint}`);
  }

  return response.json();
}

export async function POST(request) {
  try {
    const body = await request.json();

    const {
      action,
      topic,
      difficulty,
      problem,
      solution,
      count,
      question,
    } = body;

    if (action === "generate") {
      const data = await callBackend("/generate-dsa-problem", {
        topic,
        difficulty,
      });

      return Response.json({
        ...data,
        starter_code: extractStarterCode(data.problem || ""),
      });
    }

    if (action === "generateMockSet") {
      const data = await callBackend("/generate-dsa-mock-set", {
        topic,
        difficulty: difficulty || "Mixed",
        count: count || 10,
      });

      return Response.json(data);
    }

    if (action === "generateFromQuestion") {
      const selectedQuestion = question || {};

      const data = await callBackend("/generate-own-dsa-question", {
        title: selectedQuestion.title || "DSA Practice Problem",
        topic: selectedQuestion.topic || topic || "Arrays",
        difficulty: selectedQuestion.difficulty || difficulty || "Medium",
        pattern: selectedQuestion.pattern || "General DSA",
      });

      return Response.json({
        ...data,
        starter_code: extractStarterCode(data.problem || ""),
      });
    }

    if (action === "evaluate") {
      const data = await callBackend("/evaluate-dsa-solution", {
        topic,
        difficulty,
        problem,
        solution,
      });

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