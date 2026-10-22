"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { averageScore, formatScore } from "@/lib/scoring";

export default function DSAHistoryCard() {
  const [dsaHistory, setDsaHistory] = useState([]);

  useEffect(() => {
    const savedHistory = localStorage.getItem("conceptviva_dsa_history");

    if (savedHistory) {
      try {
        setDsaHistory(JSON.parse(savedHistory));
      } catch {
        setDsaHistory([]);
      }
    }
  }, []);

  function clearDsaHistory() {
    setDsaHistory([]);
    localStorage.removeItem("conceptviva_dsa_history");
  }

  const totalAttempts = dsaHistory.length;

  // Unscored attempts (AI unavailable) are excluded from the average.
  const localAverage = formatScore(averageScore(dsaHistory));

  const todayDate = new Date().toLocaleDateString();

  const solvedToday = dsaHistory.filter(
    (item) => item.date === todayDate
  ).length;

  const practiceCount = dsaHistory.filter(
    (item) => item.mode === "Practice"
  ).length;

  const mockCount = dsaHistory.filter(
    (item) => item.mode === "Mock Interview"
  ).length;

  return (
    <div className="mt-10 w-full max-w-6xl rounded-3xl border border-slate-700 bg-slate-950/70 p-4 shadow-2xl">
      <div className="mb-5 border-b border-slate-800 pb-5">
        <Link
          href="/dsa"
          className="text-sm font-semibold text-cyan-300 hover:text-cyan-200"
        >
          ← Back to DSA Home
        </Link>

        <p className="mt-3 text-sm font-semibold uppercase tracking-widest text-cyan-300">
          DSA Tracking
        </p>

        <h2 className="mt-2 text-3xl font-bold text-white">
          Practice &amp; Mock Interview History
        </h2>

        <p className="mt-1 text-base text-slate-400">
          Combined history from Practice and Mock Interview attempts. Open
          Dashboard for full backend-saved records.
        </p>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-5">
        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Total Attempts</p>
          <p className="mt-1 text-3xl font-bold text-white">{totalAttempts}</p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Average Score</p>
          <p className="mt-1 text-3xl font-bold text-white">
            {localAverage}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Solved Today</p>
          <p className="mt-1 text-3xl font-bold text-white">{solvedToday}</p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Practice Attempts</p>
          <p className="mt-1 text-3xl font-bold text-white">
            {practiceCount}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Mock Interview Attempts</p>
          <p className="mt-1 text-3xl font-bold text-white">{mockCount}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-white">
              Recent DSA Attempts
            </h3>
            <p className="text-sm text-slate-400">
              This section shows browser history for quick review.
            </p>
          </div>

          <button
            onClick={clearDsaHistory}
            disabled={dsaHistory.length === 0}
            className="rounded-xl bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-50"
          >
            Clear Local History
          </button>
        </div>

        {dsaHistory.length > 0 ? (
          <div className="max-h-[600px] overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-700">
                  <th className="py-3 pr-3">Date</th>
                  <th className="py-3 pr-3">Mode</th>
                  <th className="py-3 pr-3">Problem</th>
                  <th className="py-3 pr-3">Topic</th>
                  <th className="py-3 pr-3">Difficulty</th>
                  <th className="py-3 pr-3">Score</th>
                  <th className="py-3 pr-3">Tests</th>
                  <th className="py-3 pr-3">Status</th>
                </tr>
              </thead>

              <tbody>
                {dsaHistory.map((item) => (
                  <tr key={item.id} className="border-b border-slate-800">
                    <td className="py-3 pr-3 text-slate-300">
                      {item.date} {item.time}
                    </td>
                    <td className="py-3 pr-3 text-slate-300">
                      {item.mode || "Practice"}
                    </td>
                    <td className="py-3 pr-3 font-semibold text-white">
                      {item.problemName}
                    </td>
                    <td className="py-3 pr-3 text-slate-300">{item.topic}</td>
                    <td className="py-3 pr-3 text-slate-300">
                      {item.difficulty}
                    </td>
                    <td className="py-3 pr-3 font-bold text-white">
                      {formatScore(item.score)}
                    </td>
                    <td className="py-3 pr-3 text-xs text-slate-400">
                      {item.tests || "—"}
                    </td>
                    <td className="py-3 pr-3">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          item.status === "Good"
                            ? "bg-emerald-950/40 text-emerald-300"
                            : "bg-yellow-950/40 text-yellow-300"
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center">
            <p className="font-semibold text-white">No DSA history yet</p>
            <p className="mt-2 text-sm text-slate-400">
              Submit a solution in Practice or Mock Interview mode to start
              tracking.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
