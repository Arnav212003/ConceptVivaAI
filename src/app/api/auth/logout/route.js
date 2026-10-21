import { proxyToBackend } from "@/lib/backendProxy";

export async function POST(request) {
  return proxyToBackend(request, "/auth/logout", { method: "POST" });
}
