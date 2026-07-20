import Link from "next/link";

export default function DSAPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-white">
      <section className="mx-auto max-w-7xl">
        <div className="mb-8 rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-6 shadow-2xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-cyan-300">
            ConceptVivaAI DSA Mode
          </p>

          <h1 className="mt-3 text-4xl font-bold text-white md:text-5xl">
            DSA Coding Practice
          </h1>

          <p className="mt-3 max-w-3xl text-base leading-7 text-slate-400">
            Practice topic-wise DSA problems, write LeetCode-style solutions,
            run/evaluate your code, and get AI feedback with optimized approach,
            time complexity, space complexity, and test case analysis.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <Link
            href="/dsa/practice"
            className="group rounded-3xl border border-pink-400/30 bg-slate-900/80 p-8 shadow-2xl transition hover:-translate-y-1 hover:border-pink-300 hover:bg-slate-900"
          >
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-pink-500/20 text-4xl">
              💻
            </div>

            <h2 className="text-2xl font-bold text-white">Practice</h2>

            <p className="mt-4 text-base leading-7 text-slate-400">
              Pick a topic and difficulty, get one LeetCode-style question at
              a time, and submit for AI evaluation.
            </p>

            <p className="mt-8 font-semibold text-pink-300 transition group-hover:translate-x-2">
              Start Practice →
            </p>
          </Link>

          <Link
            href="/dsa/mock"
            className="group rounded-3xl border border-emerald-400/30 bg-slate-900/80 p-8 shadow-2xl transition hover:-translate-y-1 hover:border-emerald-300 hover:bg-slate-900"
          >
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/20 text-4xl">
              🎯
            </div>

            <h2 className="text-2xl font-bold text-white">Mock Interview</h2>

            <p className="mt-4 text-base leading-7 text-slate-400">
              Generate a 10-question mixed set (3 Easy, 4 Medium, 3 Hard) and
              simulate a real coding interview round.
            </p>

            <p className="mt-8 font-semibold text-emerald-300 transition group-hover:translate-x-2">
              Start Mock Interview →
            </p>
          </Link>

          <Link
            href="/dsa/history"
            className="group rounded-3xl border border-cyan-400/30 bg-slate-900/80 p-8 shadow-2xl transition hover:-translate-y-1 hover:border-cyan-300 hover:bg-slate-900"
          >
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-cyan-500/20 text-4xl">
              📊
            </div>

            <h2 className="text-2xl font-bold text-white">
              Tracking &amp; History
            </h2>

            <p className="mt-4 text-base leading-7 text-slate-400">
              See your total attempts, average score, and a full record of
              past practice and mock interview submissions.
            </p>

            <p className="mt-8 font-semibold text-cyan-300 transition group-hover:translate-x-2">
              View History →
            </p>
          </Link>
        </div>
      </section>
    </main>
  );
}
