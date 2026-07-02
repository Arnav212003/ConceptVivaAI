import Link from "next/link";
import DSAPracticeCard from "@/components/DSAPracticeCard";

export default function DSAPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <Link
              href="/"
              className="text-sm font-semibold text-pink-300 hover:text-pink-200"
            >
              ← Back to Domains
            </Link>

            <h1 className="mt-3 text-4xl font-extrabold">
              DSA Coding Practice
            </h1>

            <p className="mt-2 max-w-3xl text-slate-400">
              Curated DSA practice with Monaco editor, real Python test runner,
              expected vs actual output, optimized solution, and practice
              history.
            </p>
          </div>

          <div className="rounded-2xl border border-pink-400/30 bg-pink-950/20 px-5 py-3 text-sm font-semibold text-pink-300">
            Coding Practice Mode
          </div>
        </div>

        <DSAPracticeCard />
      </div>
    </main>
  );
}