import { proxyToBackend } from "@/lib/backendProxy";

// Google redirects the browser here (OAUTH_REDIRECT_URI). The backend validates
// state, exchanges the code and answers with a redirect plus Set-Cookie headers,
// which proxyToBackend relays to the browser on this origin.
export async function GET(request) {
  const { search } = new URL(request.url);
  return proxyToBackend(request, `/auth/google/callback${search}`);
}
