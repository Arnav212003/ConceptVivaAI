import { proxyToBackend } from "@/lib/backendProxy";

export async function POST(request) {
  const body = await request.text();
  if (body.length > 500) {
    return Response.json({ recorded: false }, { status: 413 });
  }
  return proxyToBackend(request, "/analytics/event", { method: "POST", body, anonymous: true });
}
