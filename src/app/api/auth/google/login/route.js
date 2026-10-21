import { proxyToBackend } from "@/lib/backendProxy";

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const returnTo = encodeURIComponent(searchParams.get("return_to") || "/dashboard");
  return proxyToBackend(request, `/auth/google/login?return_to=${returnTo}`);
}
