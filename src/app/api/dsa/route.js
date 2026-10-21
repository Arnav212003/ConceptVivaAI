import { proxyAction, proxyToBackend } from "@/lib/backendProxy";

const ACTIONS = {
  generate: "/generate-dsa-problem",
  generateMockSet: "/generate-dsa-mock-set",
  generateFromQuestion: "/generate-own-dsa-question",
  generateAI: "/generate-ai-practice-question",
  evaluate: "/evaluate-dsa-solution",
  run: "/dsa/run",
  submit: "/dsa/submissions",
  save: "/save-dsa-attempt",
  translateHindi: "/translate-to-hindi",
};

const SUBMISSION_ID = /^sub_[a-f0-9]{24}$/;

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const resource = searchParams.get("resource");

  if (resource === "bank-stats") {
    return proxyToBackend(request, "/dsa-question-bank/stats");
  }

  if (resource === "submission") {
    const id = searchParams.get("id") || "";
    if (!SUBMISSION_ID.test(id)) {
      return Response.json({ error: "Invalid submission id." }, { status: 400 });
    }
    return proxyToBackend(request, `/dsa/submissions/${id}`);
  }

  return proxyToBackend(request, "/dsa-question-bank");
}

export async function POST(request) {
  return proxyAction(request, ACTIONS, "generate");
}
