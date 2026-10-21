"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { clearSession, getCsrfToken, getStoredSession } from "@/utils/session";

const AuthContext = createContext({
  status: "loading",
  user: null,
  googleEnabled: false,
  notice: "",
  signIn: () => {},
  signOut: async () => {},
  dismissNotice: () => {},
});

async function migrateGuestHistory() {
  const guest = getStoredSession();
  if (!guest.sessionId || !guest.sessionToken) return null;

  const response = await fetch("/api/auth/migrate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": guest.sessionId,
      "X-Session-Token": guest.sessionToken,
      "X-CSRF-Token": getCsrfToken(),
    },
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({}));
  if (response.ok) {
    // The guest token is revoked server-side after a merge; start clean.
    clearSession();
  }
  return { ok: response.ok, ...data };
}

export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: "loading", user: null, googleEnabled: false });
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/me", { cache: "no-store" });
      const data = await response.json();
      setState({
        status: data.authenticated ? "authenticated" : "guest",
        user: data.user || null,
        googleEnabled: Boolean(data.google_oauth_enabled),
      });
      return data;
    } catch {
      setState({ status: "guest", user: null, googleEnabled: false });
      return null;
    }
  }, []);

  useEffect(() => {
    async function init() {
      const data = await refresh();
      const url = new URL(window.location.href);

      if (url.searchParams.get("auth_error")) {
        setNotice("Google sign-in did not complete. You can keep practising as a guest.");
      }

      if (url.searchParams.get("login") === "success" && data?.authenticated) {
        try {
          const result = await migrateGuestHistory();
          if (result?.ok && result.rows_moved > 0) {
            setNotice(`Signed in. ${result.rows_moved} saved attempt(s) from this browser were moved to your account.`);
          } else {
            setNotice("Signed in. Your progress now follows your Google account across devices.");
          }
        } catch {
          setNotice("Signed in, but guest history could not be moved. Your account works normally.");
        }
      }

      if (url.searchParams.has("login") || url.searchParams.has("auth_error")) {
        url.searchParams.delete("login");
        url.searchParams.delete("auth_error");
        window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
      }
    }
    init();
  }, [refresh]);

  const signIn = useCallback(() => {
    const returnTo = `${window.location.pathname}${window.location.search}`;
    window.location.href = `/api/auth/google/login?return_to=${encodeURIComponent(returnTo)}`;
  }, []);

  const signOut = useCallback(async () => {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": getCsrfToken() },
      cache: "no-store",
    }).catch(() => null);
    setState((current) => ({ ...current, status: "guest", user: null }));
    window.location.href = "/";
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, notice, signIn, signOut, dismissNotice: () => setNotice("") }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
