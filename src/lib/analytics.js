// First-party, anonymous product analytics. Sends only an allowlisted event name
// and dimension (no ids, no free text). Nothing is sent when the browser asks
// not to be tracked. The backend stores daily aggregate counts only.

export const TRACKED_ROUTES = new Set([
  "/", "/ml", "/ml/practice", "/ml/interview", "/ml/project",
  "/dsa", "/dsa/practice", "/dsa/mock", "/dsa/history", "/dashboard",
]);

export function trackingAllowed() {
  if (typeof navigator === "undefined") return false;
  return navigator.doNotTrack !== "1" && navigator.globalPrivacyControl !== true;
}

export function track(event, dimension = "") {
  if (!trackingAllowed()) return;
  const body = JSON.stringify({ event, dimension });
  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/analytics", new Blob([body], { type: "application/json" }));
      return;
    }
    fetch("/api/analytics", { method: "POST", body, headers: { "Content-Type": "application/json" }, keepalive: true });
  } catch {
    // Analytics must never break the app.
  }
}
