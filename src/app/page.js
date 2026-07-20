import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="mb-12 text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-300">
            ConceptVivaAI
          </p>

          <h1 className="mt-4 text-4xl font-extrabold md:text-6xl">
            Choose Your Practice Domain
          </h1>

          <p className="mx-auto mt-5 max-w-3xl text-lg leading-8 text-slate-400">
            Select a domain and start focused practice. Each domain has its
            own dedicated page, practice flow, history, and performance
            tracking.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Link
            href="/ml"
            className="group rounded-3xl border border-cyan-400/30 bg-slate-900/80 p-8 shadow-2xl transition hover:-translate-y-1 hover:border-cyan-300 hover:bg-slate-900"
          >
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-cyan-500/20 text-4xl">
              🤖
            </div>

            <h2 className="text-3xl font-bold text-white">
              ML Interview Practice
            </h2>

            <p className="mt-4 text-base leading-7 text-slate-400">
              Practice topic-wise machine learning interviews with voice-based
              questions, AI evaluation, follow-ups, and final interview report.
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              <span className="rounded-full bg-cyan-950/60 px-3 py-1 text-xs font-semibold text-cyan-300">
                Voice Interview
              </span>
              <span className="rounded-full bg-cyan-950/60 px-3 py-1 text-xs font-semibold text-cyan-300">
                Follow-ups
              </span>
              <span className="rounded-full bg-cyan-950/60 px-3 py-1 text-xs font-semibold text-cyan-300">
                Report
              </span>
            </div>

            <p className="mt-8 font-semibold text-cyan-300 transition group-hover:translate-x-2">
              Start ML Practice →
            </p>
          </Link>

          <Link
            href="/dsa"
            className="group rounded-3xl border border-pink-400/30 bg-slate-900/80 p-8 shadow-2xl transition hover:-translate-y-1 hover:border-pink-300 hover:bg-slate-900"
          >
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-pink-500/20 text-4xl">
              💻
            </div>

            <h2 className="text-3xl font-bold text-white">
              DSA Coding Practice
            </h2>

            <p className="mt-4 text-base leading-7 text-slate-400">
              Practice curated DSA problems in a LeetCode-style editor with real
              Python test cases, expected vs actual output, and history.
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              <span className="rounded-full bg-pink-950/60 px-3 py-1 text-xs font-semibold text-pink-300">
                Monaco Editor
              </span>
              <span className="rounded-full bg-pink-950/60 px-3 py-1 text-xs font-semibold text-pink-300">
                Test Runner
              </span>
              <span className="rounded-full bg-pink-950/60 px-3 py-1 text-xs font-semibold text-pink-300">
                History
              </span>
            </div>

            <p className="mt-8 font-semibold text-pink-300 transition group-hover:translate-x-2">
              Start DSA Practice →
            </p>
          </Link>
        </div>

        <div className="mt-8 rounded-3xl border border-slate-700 bg-slate-900/60 p-6">
          <h3 className="text-xl font-bold text-white">Future Domains</h3>

          <p className="mt-2 text-slate-400">
            Later you can add SQL, Power BI, System Design, Aptitude, Legal, or
            any subject as a separate domain page without disturbing existing
            ML and DSA modules.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-4">
            <div className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4 text-center text-slate-300">
              SQL
            </div>

            <div className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4 text-center text-slate-300">
              Power BI
            </div>

            <div className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4 text-center text-slate-300">
              System Design
            </div>

            <div className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4 text-center text-slate-300">
              Aptitude
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}