import { proxyAction } from "@/lib/backendProxy";

const ACTIONS = {
  generate: "/generate-project-challenge",
  evaluate: "/evaluate-project-submission",
  save: "/save-project-attempt",
};

export async function POST(request) {
  return proxyAction(request, ACTIONS, "generate");
}
