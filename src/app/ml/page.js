import Link from "next/link";
import InterviewCard from "@/components/InterviewCard";

export default function MLPage() {
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
              ML Interview Practice
            </h1>

            <p className="mt-2 max-w-3xl text-slate-400">
              Topic-wise machine learning mock interview with voice questions,
              answer evaluation, follow-up questions, and final report.
            </p>
          </div>

          <div className="rounded-2xl border border-cyan-400/30 bg-cyan-950/20 px-5 py-3 text-sm font-semibold text-cyan-300">
            Voice Interview Mode
          </div>
        </div>

        <InterviewCard />
      </div>
    </main>
  );
}