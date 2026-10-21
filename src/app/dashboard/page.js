"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CompactRecord,
  ModuleCard,
  OverviewCard,
  ProgressBar,
  SectionCard,
  SkeletonGrid,
  buildTimeline,
  buildTopicReadiness,
  formatDate,
  readinessLabel,
} from "@/components/dashboard/widgets";
import { useAuth } from "@/components/AuthProvider";
import { EmptyState, ErrorBanner } from "@/components/ui";
import { apiGet } from "@/lib/api";
import { formatScore, scoreTone } from "@/lib/scoring";

const MODULES = [
  ["ml_practice", "ML Practice", "Topic-wise AI evaluation for concepts, definitions, examples, and interview-style answers."],
  ["dsa_practice", "DSA Practice", "LeetCode-style practice with hidden-test judging, AI review, optimized approach and complexity."],
  ["project_challenge", "Project Challenge", "Mini project and hackathon-style challenges for ML, Analytics, DSA, and System Design."],
  ["voice_interview", "Voice Interview", "Spoken mock interview with follow-ups, scoring, and a final report."],
];

export default function DashboardPage() {
  const { status, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [statsData, historyData] = await Promise.all([
        apiGet("/api/dashboard"),
        apiGet("/api/history?limit=50&offset=0"),
      ]);
      setStats(statsData);
      setHistory(historyData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const timeline = useMemo(() => buildTimeline(history), [history]);
  const topicReadiness = useMemo(() => buildTopicReadiness(timeline), [timeline]);

  const moduleAverages = MODULES.map(([key]) => stats?.[key])
    .filter((item) => item && (item.scored_attempts ?? item.total_interviews ?? 0) > 0)
    .map((item) => Number(item.average_score || 0));
  const overallReadiness = moduleAverages.length
    ? Math.round((moduleAverages.reduce((sum, value) => sum + value, 0) / moduleAverages.length) * 10)
    : 0;

  const scoredAverage = (key) => {
    const item = stats?.[key];
    const scored = item?.scored_attempts ?? item?.total_interviews ?? 0;
    return formatScore(scored > 0 ? item.average_score : null);
  };

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-white">
      <section className="mx-auto max-w-7xl">
        <div className="mb-8 overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 shadow-2xl">
          <div className="flex flex-col gap-6 p-6 md:p-8 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-widest text-cyan-300">ConceptVivaAI Dashboard</p>
              <h1 className="mt-3 text-4xl font-bold text-white md:text-5xl">Progress, Readiness & History</h1>
              <p className="mt-3 max-w-3xl text-base leading-7 text-slate-400">
                {status === "authenticated"
                  ? `Signed in as ${user?.name || user?.email}. Your progress is saved to your account.`
                  : "Guest mode: progress is saved for this browser. Sign in with Google to keep it across devices."}
              </p>
              <button
                onClick={load}
                disabled={loading}
                className="mt-6 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-cyan-600 disabled:opacity-60"
              >
                {loading ? "Loading..." : "Refresh Dashboard"}
              </button>
            </div>

            <div className="rounded-3xl border border-cyan-400/30 bg-cyan-950/20 p-6 text-center">
              <p className="text-sm text-cyan-200">Overall Readiness</p>
              <p className="mt-2 text-6xl font-black text-white" data-testid="overall-readiness">{overallReadiness}%</p>
              <p className="mt-2 text-sm font-semibold text-cyan-200">{readinessLabel(overallReadiness)}</p>
              <ProgressBar value={overallReadiness} />
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} onRetry={load} />
          </div>
        )}

        {loading && !stats ? (
          <SkeletonGrid />
        ) : (
          stats && (
            <>
              <div className="mb-8 grid gap-4 sm:grid-cols-2 md:grid-cols-4">
                <OverviewCard
                  label="Total Activity"
                  value={stats.overall?.total_activity ?? 0}
                  subtext={
                    stats.overall?.unavailable_attempts
                      ? `${stats.overall.unavailable_attempts} not scored (AI was unavailable)`
                      : "All saved backend records"
                  }
                />
                <OverviewCard label="ML Practice" value={stats.ml_practice?.total_attempts ?? 0} subtext={`${scoredAverage("ml_practice")} average`} />
                <OverviewCard label="DSA Attempts" value={stats.dsa_practice?.total_attempts ?? 0} subtext={`${scoredAverage("dsa_practice")} average`} />
                <OverviewCard label="Voice Interviews" value={stats.voice_interview?.total_interviews ?? 0} subtext={`${scoredAverage("voice_interview")} average`} />
              </div>

              <div className="mb-8 grid gap-5 lg:grid-cols-2">
                {MODULES.map(([key, title, description]) => (
                  <ModuleCard
                    key={key}
                    title={title}
                    description={description}
                    stats={stats[key]}
                    tierBreakdown={key === "dsa_practice" && stats.dsa_practice?.verified ? stats.dsa_practice : null}
                  />
                ))}
              </div>
            </>
          )
        )}

        <div className="mb-8 grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <SectionCard title="Recent Activity Timeline">
              {timeline.length > 0 ? (
                <div className="space-y-3">
                  {timeline.slice(0, 12).map((item) => {
                    const tone = scoreTone(item.score);
                    return (
                      <div key={item.id} className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div className="min-w-0">
                            <p className="text-xs font-semibold uppercase tracking-widest text-cyan-300">{item.type}</p>
                            <p className="mt-1 break-words font-semibold text-white">{item.title}</p>
                            <p className="mt-1 text-sm leading-6 text-slate-400">{item.subtitle}</p>
                            <p className="mt-1 text-xs text-slate-500">{formatDate(item.created_at)}</p>
                          </div>
                          <span className={`self-start whitespace-nowrap rounded-full border ${tone.border} px-3 py-1 text-xs font-semibold ${tone.text}`}>
                            {formatScore(item.score)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  title="No activity yet"
                  message="Complete ML, DSA, Project, or Voice Interview practice to build your timeline."
                />
              )}
            </SectionCard>
          </div>

          <SectionCard title="Topic-wise Readiness">
            {topicReadiness.length > 0 ? (
              <div className="space-y-4">
                {topicReadiness.map((item) => (
                  <div key={item.topic} className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="break-words font-semibold text-white">{item.topic}</p>
                        <p className="mt-1 text-xs text-slate-500">{item.attempts} scored attempt(s) · {item.types}</p>
                      </div>
                      <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-200">{item.readiness}%</span>
                    </div>
                    <ProgressBar value={item.readiness} />
                    <p className="mt-2 text-xs text-slate-400">Avg Score: {formatScore(item.averageScore)}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No topic data yet" message="Practice any topic and it will appear here." />
            )}
          </SectionCard>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {[
            ["Recent ML Practice", "ml-", "No ML practice saved"],
            ["Recent DSA Attempts", "dsa-", "No DSA attempt saved"],
            ["Recent Project Challenges", "project-", "No project challenge saved"],
            ["Recent Voice Interviews", "voice-", "No voice interview saved"],
          ].map(([title, prefix, emptyTitle]) => {
            const records = timeline.filter((item) => item.id.startsWith(prefix)).slice(0, 8);
            return (
              <SectionCard key={title} title={title}>
                {records.length > 0 ? (
                  <div className="space-y-3">
                    {records.map((item) => (
                      <CompactRecord key={item.id} title={item.title} subtitle={item.subtitle} date={item.created_at} />
                    ))}
                  </div>
                ) : (
                  <EmptyState title={emptyTitle} message="No saved records found yet." />
                )}
              </SectionCard>
            );
          })}
        </div>
      </section>
    </main>
  );
}
