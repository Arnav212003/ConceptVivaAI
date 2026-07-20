import Link from "next/link";
import InterviewCard from "@/components/InterviewCard";

export default function MLInterviewPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <Link
          href="/ml"
          className="text-sm font-semibold text-pink-300 hover:text-pink-200"
        >
          ← Back to ML Home
        </Link>

        <InterviewCard />
      </div>
    </main>
  );
}