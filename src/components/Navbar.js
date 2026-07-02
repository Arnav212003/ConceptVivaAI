"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

  function isActive(path) {
    return pathname === path;
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
        </div>

        <div className="md:hidden">
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
          </select>
        </div>
      </nav>
    </header>
  );
}