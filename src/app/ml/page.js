import Link from "next/link";

export default function MLPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6">
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

        <div className="grid gap-6 md:grid-cols-3">
          <Link
            href="/ml/practice"
            className="group rounded-3xl border border-cyan-400/30 bg-slate-900/80 p-8 shadow-2xl transition hover:-translate-y-1 hover:border-cyan-300 hover:bg-slate-900"
          >
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-cyan-500/20 text-4xl">
              🤖
            </div>

            <h2 className="text-2xl font-bold text-white">Practice Mode</h2>

            <p className="mt-4 text-base leading-7 text-slate-400">
              AI gives topic-wise theoretical questions. You type your answer
              and get instant feedback.
            </p>

            <p className="mt-8 font-semibold text-cyan-300 transition group-hover:translate-x-2">
              Start Practice →
            </p>
          </Link>

          <Link
            href="/ml/interview"
            className="group rounded-3xl border border-pink-400/30 bg-slate-900/80 p-8 shadow-2xl transition hover:-translate-y-1 hover:border-pink-300 hover:bg-slate-900"
          >
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-pink-500/20 text-4xl">
              🎙️
            </div>

            <h2 className="text-2xl font-bold text-white">
              Voice Mock Interview
            </h2>

            <p className="mt-4 text-base leading-7 text-slate-400">
              AI speaks questions, listens to your answer, asks follow-ups,
              and generates a final report.
            </p>

            <p className="mt-8 font-semibold text-pink-300 transition group-hover:translate-x-2">
              Start Interview →
            </p>
          </Link>

          <Link
            href="/ml/project"
            className="group rounded-3xl border border-emerald-400/30 bg-slate-900/80 p-8 shadow-2xl transition hover:-translate-y-1 hover:border-emerald-300 hover:bg-slate-900"
          >
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/20 text-4xl">
              🎯
            </div>

            <h2 className="text-2xl font-bold text-white">
              Project Challenge
            </h2>

            <p className="mt-4 text-base leading-7 text-slate-400">
              AI generates a hackathon-style project problem with dataset
              schema, tasks, metrics, and review.
            </p>

            <p className="mt-8 font-semibold text-emerald-300 transition group-hover:translate-x-2">
              Start Project →
            </p>
          </Link>
        </div>
      </div>
    </main>
  );
}