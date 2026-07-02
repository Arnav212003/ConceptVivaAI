"use client";

import { useState } from "react";
import Link from "next/link";
import InterviewCard from "@/components/InterviewCard";
import MLPracticeCard from "@/components/MLPracticeCard";
import ProjectChallengeCard from "@/components/ProjectChallengeCard";

export default function MLPage() {
  const [mode, setMode] = useState("practice");

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link
              href="/"
              className="text-sm font-semibold text-cyan-300 hover:text-cyan-200"
            >
              ← Back to Domains
            </Link>

            <h1 className="mt-3 text-4xl font-extrabold">
              ML AI Practice & Interview
            </h1>

            <p className="mt-2 max-w-3xl text-slate-400">
              Practice machine learning topics through AI-generated questions,
              voice mock interviews, and project-based challenges.
            </p>
          </div>

          <div className="rounded-2xl border border-cyan-400/30 bg-cyan-950/20 px-5 py-3 text-sm font-semibold text-cyan-300">
            Topic-wise AI Assessment
          </div>
        </div>

        <div className="mb-8 grid gap-4 md:grid-cols-3">
          <button
            onClick={() => setMode("practice")}
            className={`rounded-2xl border p-5 text-left transition ${
              mode === "practice"
                ? "border-cyan-400 bg-cyan-950/30"
                : "border-slate-700 bg-slate-900/70 hover:border-slate-500"
            }`}
          >
            <p className="text-xl font-bold text-white">Practice Mode</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              AI gives topic-wise theoretical questions. You type your answer
              and get instant feedback.
            </p>
          </button>

          <button
            onClick={() => setMode("mock")}
            className={`rounded-2xl border p-5 text-left transition ${
              mode === "mock"
                ? "border-pink-400 bg-pink-950/30"
                : "border-slate-700 bg-slate-900/70 hover:border-slate-500"
            }`}
          >
            <p className="text-xl font-bold text-white">Voice Mock Interview</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              AI speaks questions, listens to your answer, asks follow-ups, and
              generates a final report.
            </p>
          </button>

          <button
            onClick={() => setMode("project")}
            className={`rounded-2xl border p-5 text-left transition ${
              mode === "project"
                ? "border-emerald-400 bg-emerald-950/30"
                : "border-slate-700 bg-slate-900/70 hover:border-slate-500"
            }`}
          >
            <p className="text-xl font-bold text-white">Project Challenge</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              AI generates a hackathon-style project problem with dataset
              schema, tasks, metrics, and review.
            </p>
          </button>
        </div>

        {mode === "practice" && <MLPracticeCard />}
        {mode === "mock" && <InterviewCard />}
        {mode === "project" && <ProjectChallengeCard />}
      </div>
    </main>
  );
}