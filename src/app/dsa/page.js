import DSAPracticeCard from "@/components/DSAPracticeCard";

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

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
              <p className="text-sm text-slate-400">Mode</p>
              <p className="mt-1 text-xl font-bold text-white">
                Practice + Evaluation
              </p>
            </div>

            <div className="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
              <p className="text-sm text-slate-400">Question Style</p>
              <p className="mt-1 text-xl font-bold text-white">
                LeetCode-style
              </p>
            </div>

            <div className="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
              <p className="text-sm text-slate-400">Tracking</p>
              <p className="mt-1 text-xl font-bold text-white">
                Attempts + Scores
              </p>
            </div>
          </div>
        </div>

        <DSAPracticeCard />
      </section>
    </main>
  );
}