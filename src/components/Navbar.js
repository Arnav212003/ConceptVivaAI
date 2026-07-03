"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { logoutConceptVivaSession } from "@/utils/session";

export default function Navbar() {
  const pathname = usePathname();
  const [loggingOut, setLoggingOut] = useState(false);

  function isActive(path) {
    return pathname === path;
  }

  async function handleLogout() {
    const confirmed = window.confirm(
      "Reset current session? Your current session token will be revoked and a fresh session will be created on next use."
    );

    if (!confirmed) return;

    setLoggingOut(true);

    await logoutConceptVivaSession();

    setLoggingOut(false);

    window.location.href = "/";
  }

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 text-white">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-pink-500 text-xl font-black text-white shadow-lg">
            CV
          </div>

          <div>
            <h1 className="text-xl font-extrabold leading-none">
              ConceptVivaAI
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              AI Interview & DSA Coach
            </p>
          </div>
        </Link>

        <div className="hidden items-center gap-2 md:flex">
          <Link
            href="/"
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              isActive("/")
                ? "bg-slate-800 text-white"
                : "text-slate-300 hover:bg-slate-900 hover:text-white"
            }`}
          >
            Home
          </Link>

          <Link
            href="/ml"
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              isActive("/ml")
                ? "bg-cyan-500/20 text-cyan-300"
                : "text-slate-300 hover:bg-slate-900 hover:text-white"
            }`}
          >
            ML Interview
          </Link>

          <Link
            href="/dsa"
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              isActive("/dsa")
                ? "bg-pink-500/20 text-pink-300"
                : "text-slate-300 hover:bg-slate-900 hover:text-white"
            }`}
          >
            DSA Practice
          </Link>

          <Link
            href="/dashboard"
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              isActive("/dashboard")
                ? "bg-emerald-500/20 text-emerald-300"
                : "text-slate-300 hover:bg-slate-900 hover:text-white"
            }`}
          >
            Dashboard
          </Link>

          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-300 transition hover:bg-red-500/20 hover:text-red-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loggingOut ? "Resetting..." : "Reset Session"}
          </button>
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <select
            value={pathname}
            onChange={(e) => {
              window.location.href = e.target.value;
            }}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none"
          >
            <option value="/">Home</option>
            <option value="/ml">ML Interview</option>
            <option value="/dsa">DSA Practice</option>
            <option value="/dashboard">Dashboard</option>
          </select>

          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="rounded-xl border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-300 transition hover:bg-red-500/20 disabled:opacity-60"
          >
            Reset
          </button>
        </div>
      </nav>
    </header>
  );
}