"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { logoutConceptVivaSession } from "@/utils/session";

const LINKS = [
  ["/", "Home", "bg-slate-800 text-white"],
  ["/ml", "ML Interview", "bg-cyan-500/20 text-cyan-300"],
  ["/dsa", "DSA Practice", "bg-pink-500/20 text-pink-300"],
  ["/dashboard", "Dashboard", "bg-emerald-500/20 text-emerald-300"],
];

function isActive(pathname, href) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function AccountControls({ compact = false }) {
  const { status, user, googleEnabled, signIn, signOut } = useAuth();
  const [resetting, setResetting] = useState(false);

  async function resetGuestSession() {
    const confirmed = window.confirm(
      "Reset current session? Your guest session token will be revoked and a fresh session will be created on next use."
    );
    if (!confirmed) return;
    setResetting(true);
    await logoutConceptVivaSession();
    setResetting(false);
    window.location.href = "/";
  }

  if (status === "loading") return <span className="h-9 w-24 animate-pulse rounded-xl bg-slate-800" aria-hidden />;

  if (status === "authenticated") {
    return (
      <div className="flex items-center gap-2">
        <span className="hidden max-w-[10rem] truncate text-sm text-slate-300 lg:inline" title={user?.email}>
          {user?.name || user?.email}
        </span>
        <button
          onClick={signOut}
          className="rounded-xl border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${compact ? "flex-col items-stretch" : ""}`}>
      {googleEnabled && (
        <button
          onClick={signIn}
          className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-slate-200"
        >
          Sign in with Google
        </button>
      )}
      <button
        onClick={resetGuestSession}
        disabled={resetting}
        className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-300 transition hover:bg-red-500/20 disabled:opacity-60"
      >
        {resetting ? "Resetting..." : "Reset Session"}
      </button>
    </div>
  );
}

function AuthNotice() {
  const { notice, dismissNotice } = useAuth();
  if (!notice) return null;
  return (
    <div role="status" className="border-b border-emerald-500/30 bg-emerald-950/40">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-2 text-sm text-emerald-100">
        <p>{notice}</p>
        <button onClick={dismissNotice} className="rounded-lg px-2 py-1 hover:bg-emerald-500/20" aria-label="Dismiss">
          ✕
        </button>
      </div>
    </div>
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 text-white sm:px-6">
        <Link href="/" className="flex min-w-0 items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-pink-500 text-xl font-black text-white shadow-lg">
            CV
          </div>
          <div className="min-w-0">
            <p className="text-xl font-extrabold leading-none">ConceptVivaAI</p>
            <p className="mt-1 truncate text-xs text-slate-400">AI Interview & DSA Coach</p>
          </div>
        </Link>

        <div className="hidden items-center gap-2 md:flex">
          {LINKS.map(([href, label, active]) => (
            <Link
              key={href}
              href={href}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                isActive(pathname, href) ? active : "text-slate-300 hover:bg-slate-900 hover:text-white"
              }`}
            >
              {label}
            </Link>
          ))}
          <AccountControls />
        </div>

        <button
          className="rounded-xl border border-slate-700 px-3 py-2 text-sm md:hidden"
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Close" : "Menu"}
        </button>
      </nav>

      {open && (
        <div id="mobile-menu" className="border-t border-slate-800 px-4 pb-4 md:hidden">
          <div className="flex flex-col gap-1 py-3">
            {LINKS.map(([href, label, active]) => (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={`rounded-xl px-4 py-3 text-sm font-semibold ${
                  isActive(pathname, href) ? active : "text-slate-300 hover:bg-slate-900"
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
          <AccountControls compact />
        </div>
      )}

      <AuthNotice />
    </header>
  );
}
