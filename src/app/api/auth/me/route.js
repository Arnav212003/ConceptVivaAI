import { proxyToBackend } from "@/lib/backendProxy";

export async function GET(request) {
  return proxyToBackend(request, "/auth/me");
}
