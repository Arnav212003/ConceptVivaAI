import Link from "next/link";
import MLPracticeCard from "@/components/MLPracticeCard";

export default function MLPracticePage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <Link
          href="/ml"
          className="text-sm font-semibold text-cyan-300 hover:text-cyan-200"
        >
          ← Back to ML Home
        </Link>

        <MLPracticeCard />
      </div>
    </main>
  );
}