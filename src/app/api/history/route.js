import { proxyToBackend } from "@/lib/backendProxy";

function clampInt(value, fallback, max) {
  const number = Number.parseInt(value ?? "", 10);
  if (Number.isNaN(number) || number < 0) return fallback;
  return Math.min(number, max);
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const limit = clampInt(searchParams.get("limit"), 20, 100);
  const offset = clampInt(searchParams.get("offset"), 0, 100000);
  return proxyToBackend(request, `/history?limit=${limit}&offset=${offset}`);
}
