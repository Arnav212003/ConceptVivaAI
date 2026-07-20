import Link from "next/link";
import ProjectChallengeCard from "@/components/ProjectChallengeCard";

export default function MLProjectPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <Link
          href="/ml"
          className="text-sm font-semibold text-emerald-300 hover:text-emerald-200"
        >
          ← Back to ML Home
        </Link>

        <ProjectChallengeCard />
      </div>
    </main>
  );
}