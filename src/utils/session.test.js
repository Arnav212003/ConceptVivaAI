import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetchWithSessionRetry, getCsrfToken, saveSession } from "@/utils/session";

describe("session helper", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the CSRF cookie", () => {
    expect(getCsrfToken()).toBe("");
    document.cookie = "cv_csrf=abc123; path=/";
    expect(getCsrfToken()).toBe("abc123");
  });

  it("sends guest headers and the CSRF token when signed in", async () => {
    saveSession("cv_guest", "1.sig", 3600);
    document.cookie = "cv_csrf=tok; path=/";
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetchWithSessionRetry("/api/dashboard", { method: "GET" });

    const headers = fetchMock.mock.calls[0][1].headers;
    expect(headers["X-Session-Id"]).toBe("cv_guest");
    expect(headers["X-Session-Token"]).toBe("1.sig");
    expect(headers["X-CSRF-Token"]).toBe("tok");
  });

  it("creates a fresh guest session once after a 401", async () => {
    saveSession("cv_old", "1.old", 3600);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("{}", { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ session_id: "cv_new", session_token: "2.new", expires_in_seconds: 60 }), {
          status: 200,
        })
      )
      .mockResolvedValueOnce(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await apiFetchWithSessionRetry("/api/dashboard", { method: "GET" });

    expect(response.status).toBe(200);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/session");
    expect(fetchMock.mock.calls[2][1].headers["X-Session-Id"]).toBe("cv_new");
  });

  it("does not replace the guest session on a CSRF 403 while signed in", async () => {
    saveSession("cv_guest", "1.sig", 3600);
    document.cookie = "cv_csrf=tok; path=/";
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 403 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await apiFetchWithSessionRetry("/api/interview", { method: "POST" });
    expect(response.status).toBe(403);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
