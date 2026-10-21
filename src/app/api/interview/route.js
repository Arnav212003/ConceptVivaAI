import { proxyAction } from "@/lib/backendProxy";

const ACTIONS = {
  question: "/generate-question",
  evaluate: "/evaluate-answer",
  save: "/save-ml-practice-attempt",
  saveInterviewReport: "/save-interview-report",
};

export async function POST(request) {
  return proxyAction(request, ACTIONS, "question");
}
