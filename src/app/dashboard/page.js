"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetchWithSessionRetry } from "@/utils/session";

function formatDate(value) {
  if (!value) return "N/A";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function getReadinessLabel(value) {
  if (value >= 80) return "Interview Ready";
  if (value >= 60) return "Good Progress";
  if (value >= 40) return "Needs Practice";
  if (value > 0) return "Revision Needed";
  return "No Data Yet";
}

function getScoreTone(value) {
  if (value >= 8) {
    return {
      text: "text-emerald-300",
      bg: "bg-emerald-500",
      border: "border-emerald-400/30",
      softBg: "bg-emerald-950/20",
    };
  }

  if (value >= 6) {
    return {
      text: "text-yellow-300",
      bg: "bg-yellow-500",
      border: "border-yellow-400/30",
      softBg: "bg-yellow-950/20",
    };
  }

  if (value > 0) {
    return {
      text: "text-red-300",
      bg: "bg-red-500",
      border: "border-red-400/30",
      softBg: "bg-red-950/20",
    };
  }

  return {
    text: "text-slate-300",
    bg: "bg-slate-600",
    border: "border-slate-700",
    softBg: "bg-slate-950/40",
  };
}

function ProgressBar({ value }) {
  const safeValue = Math.max(0, Math.min(100, Number(value || 0)));
  const scoreValue = safeValue / 10;
  const tone = getScoreTone(scoreValue);

  return (
    <div className="mt-3">
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full ${tone.bg}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
}

function OverviewCard({ label, value, subtext }) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-4xl font-bold text-white">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{subtext}</p>
    </div>
  );
}

function ModuleCard({ title, total, average, description, tierBreakdown }) {
  const readiness = Math.round(Number(average || 0) * 10);
  const tone = getScoreTone(Number(average || 0));

  return (
    <div
      className={`rounded-2xl border ${tone.border} ${tone.softBg} p-5 shadow-xl`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-white">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-400">
            {description}
          </p>
        </div>

        <span
          className={`rounded-full border ${tone.border} px-3 py-1 text-xs font-semibold ${tone.text}`}
        >
          {getReadinessLabel(readiness)}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
          <p className="text-xs text-slate-400">Total</p>
          <p className="mt-1 text-2xl font-bold text-white">{total}</p>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
          <p className="text-xs text-slate-400">Average</p>
          <p className="mt-1 text-2xl font-bold text-white">
            {Number(average || 0).toFixed(1)}/10
          </p>
        </div>
      </div>

      {tierBreakdown && (
        <div className="mt-3 grid grid-cols-2 gap-4">
          <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/20 p-4">
            <p className="text-xs font-semibold text-emerald-300">
              ✅ Verified ({tierBreakdown.verified.total_attempts})
            </p>
            <p className="mt-1 text-lg font-bold text-white">
              {Number(tierBreakdown.verified.average_score || 0).toFixed(1)}/10
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              Hidden-test scored
            </p>
          </div>

          <div className="rounded-xl border border-indigo-800/60 bg-indigo-950/20 p-4">
            <p className="text-xs font-semibold text-indigo-300">
              🤖 AI Generated ({tierBreakdown.ai_generated.total_attempts})
            </p>
            <p className="mt-1 text-lg font-bold text-white">
              {Number(tierBreakdown.ai_generated.average_score || 0).toFixed(1)}/10
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              AI-reviewed scoring
            </p>
          </div>
        </div>
      )}

      <ProgressBar value={readiness} />

      <p className="mt-2 text-xs text-slate-500">Readiness: {readiness}%</p>
    </div>
  );
}

function EmptyBox({ title, message = "No saved records found yet." }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-5 text-center">
      <p className="font-semibold text-white">{title}</p>
      <p className="mt-1 text-sm text-slate-400">{message}</p>
    </div>
  );
}

function SectionCard({ title, children }) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5 shadow-xl">
      <h2 className="mb-4 text-xl font-bold text-white">{title}</h2>
      {children}
    </div>
  );
}

function CompactRecord({ title, subtitle, date }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
      <p className="font-semibold text-white">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-400">{subtitle}</p>
      <p className="mt-1 text-xs text-slate-500">{formatDate(date)}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState(null);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const [statsResponse, historyResponse] = await Promise.all([
        apiFetchWithSessionRetry("/api/dashboard", {
          method: "GET",
        }),
        apiFetchWithSessionRetry("/api/history?limit=50&offset=0", {
          method: "GET",
        }),
      ]);

      const statsData = await statsResponse.json();
      const historyData = await historyResponse.json();

      if (!statsResponse.ok) {
        throw new Error(statsData.detail || statsData.error || "Stats failed");
      }

      if (!historyResponse.ok) {
        throw new Error(
          historyData.detail || historyData.error || "History failed"
        );
      }

      setStats(statsData);
      setHistory(historyData);
    } catch (err) {
      setError(err.message || "Dashboard load failed.");
    }

    setLoading(false);
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const mlPractice = useMemo(() => history?.ml_practice || [], [history]);
  const dsaPractice = useMemo(() => history?.dsa_practice || [], [history]);
  const projectChallenge = useMemo(
    () => history?.project_challenge || [],
    [history]
  );
  const voiceInterview = useMemo(
    () => history?.voice_interview || [],
    [history]
  );

  const mlTotal = stats?.ml_practice?.total_attempts ?? mlPractice.length ?? 0;
  const dsaTotal =
    stats?.dsa_practice?.total_attempts ?? dsaPractice.length ?? 0;
  const projectTotal =
    stats?.project_challenge?.total_attempts ?? projectChallenge.length ?? 0;
  const interviewTotal =
    stats?.voice_interview?.total_interviews ?? voiceInterview.length ?? 0;

  const mlAverage = Number(stats?.ml_practice?.average_score || 0);
  const dsaAverage = Number(stats?.dsa_practice?.average_score || 0);
  const projectAverage = Number(stats?.project_challenge?.average_score || 0);
  const interviewAverage = Number(stats?.voice_interview?.average_score || 0);

  const totalActivity =
    stats?.overall?.total_activity ??
    mlTotal + dsaTotal + projectTotal + interviewTotal;

  const activeModuleAverages = [
    mlTotal > 0 ? mlAverage : null,
    dsaTotal > 0 ? dsaAverage : null,
    projectTotal > 0 ? projectAverage : null,
    interviewTotal > 0 ? interviewAverage : null,
  ].filter((value) => value !== null);

  const overallReadiness =
    activeModuleAverages.length > 0
      ? Math.round(
          (activeModuleAverages.reduce((sum, value) => sum + value, 0) /
            activeModuleAverages.length) *
            10
        )
      : 0;

  const activityTimeline = useMemo(() => {
    const mlItems = mlPractice.map((item) => ({
      id: `ml-${item.id}`,
      type: "ML Practice",
      title: item.topic || "ML Practice",
      subtitle: `Score: ${item.score ?? 0}/10 · Verdict: ${
        item.verdict || "PARTIAL"
      }`,
      score: Number(item.score || 0),
      topic: item.topic || "Unknown Topic",
      created_at: item.created_at,
    }));

    const dsaItems = dsaPractice.map((item) => ({
      id: `dsa-${item.id}`,
      type: "DSA Attempt",
      title: item.problem_name || "DSA Problem",
      subtitle: `Topic: ${item.topic || "DSA"} · Score: ${
        item.score ?? 0
      }/10 · Status: ${item.status || "Needs Improvement"}`,
      score: Number(item.score || 0),
      topic: item.topic || "Unknown Topic",
      created_at: item.created_at,
    }));

    const projectItems = projectChallenge.map((item) => ({
      id: `project-${item.id}`,
      type: "Project Challenge",
      title: item.project_title || "Project Challenge",
      subtitle: `Topic: ${item.topic || "Project"} · Score: ${
        item.score ?? 0
      }/10 · Verdict: ${item.verdict || "PARTIAL"}`,
      score: Number(item.score || 0),
      topic: item.topic || "Unknown Topic",
      created_at: item.created_at,
    }));

    const interviewItems = voiceInterview.map((item) => ({
      id: `voice-${item.id}`,
      type: "Voice Interview",
      title: item.topic || "Voice Interview",
      subtitle: `Rounds: ${item.rounds || 0} · Average Score: ${
        item.average_score ?? 0
      }/10`,
      score: Number(item.average_score || 0),
      topic: item.topic || "Unknown Topic",
      created_at: item.created_at,
    }));

    return [...mlItems, ...dsaItems, ...projectItems, ...interviewItems]
      .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
      .slice(0, 12);
  }, [mlPractice, dsaPractice, projectChallenge, voiceInterview]);

  const topicReadiness = useMemo(() => {
    const topicMap = new Map();

    function addTopic(topic, score, type) {
      const cleanTopic = topic || "Unknown Topic";

      if (!topicMap.has(cleanTopic)) {
        topicMap.set(cleanTopic, {
          topic: cleanTopic,
          totalScore: 0,
          count: 0,
          types: new Set(),
        });
      }

      const current = topicMap.get(cleanTopic);
      current.totalScore += Number(score || 0);
      current.count += 1;
      current.types.add(type);
    }

    mlPractice.forEach((item) => addTopic(item.topic, item.score, "ML Practice"));
    dsaPractice.forEach((item) => addTopic(item.topic, item.score, "DSA"));
    projectChallenge.forEach((item) =>
      addTopic(item.topic, item.score, "Project")
    );
    voiceInterview.forEach((item) =>
      addTopic(item.topic, item.average_score, "Interview")
    );

    return Array.from(topicMap.values())
      .map((item) => ({
        topic: item.topic,
        attempts: item.count,
        readiness: Math.round((item.totalScore / item.count) * 10),
        averageScore: (item.totalScore / item.count).toFixed(1),
        types: Array.from(item.types).join(", "),
      }))
      .sort((a, b) => b.readiness - a.readiness)
      .slice(0, 10);
  }, [mlPractice, dsaPractice, projectChallenge, voiceInterview]);

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-white">
      <section className="mx-auto max-w-7xl">
        <div className="mb-8 overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 shadow-2xl">
          <div className="p-6 md:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-widest text-cyan-300">
                  ConceptVivaAI Dashboard
                </p>

                <h1 className="mt-3 text-4xl font-bold text-white md:text-5xl">
                  Progress, Readiness & History
                </h1>

                <p className="mt-3 max-w-3xl text-base leading-7 text-slate-400">
                  Track your ML practice, DSA attempts, project challenges, and
                  voice interview reports from the backend database.
                </p>

                <button
                  onClick={loadDashboard}
                  disabled={loading}
                  className="mt-6 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-cyan-600 disabled:opacity-60"
                >
                  {loading ? "Loading..." : "Refresh Dashboard"}
                </button>
              </div>

              <div className="rounded-3xl border border-cyan-400/30 bg-cyan-950/20 p-6 text-center">
                <p className="text-sm text-cyan-200">Overall Readiness</p>
                <p className="mt-2 text-6xl font-black text-white">
                  {overallReadiness}%
                </p>
                <p className="mt-2 text-sm font-semibold text-cyan-200">
                  {getReadinessLabel(overallReadiness)}
                </p>
                <ProgressBar value={overallReadiness} />
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-red-500/40 bg-red-950/30 p-5 text-red-200">
            {error}
          </div>
        )}

        <div className="mb-8 grid gap-4 md:grid-cols-4">
          <OverviewCard
            label="Total Activity"
            value={totalActivity}
            subtext="All saved backend records"
          />
          <OverviewCard
            label="ML Practice"
            value={mlTotal}
            subtext={`${mlAverage.toFixed(1)}/10 average score`}
          />
          <OverviewCard
            label="DSA Attempts"
            value={dsaTotal}
            subtext={`${dsaAverage.toFixed(1)}/10 average score`}
          />
          <OverviewCard
            label="Voice Interviews"
            value={interviewTotal}
            subtext={`${interviewAverage.toFixed(1)}/10 average score`}
          />
        </div>

        <div className="mb-8 grid gap-5 lg:grid-cols-2">
          <ModuleCard
            title="ML Practice"
            total={mlTotal}
            average={mlAverage}
            description="Topic-wise AI evaluation for concepts, definitions, examples, and interview-style answers."
          />

          <ModuleCard
            title="DSA Practice"
            total={dsaTotal}
            average={dsaAverage}
            description="LeetCode-style practice, AI review, optimized approach, complexity, and test feedback."
            tierBreakdown={
              stats?.dsa_practice?.verified && stats?.dsa_practice?.ai_generated
                ? {
                    verified: stats.dsa_practice.verified,
                    ai_generated: stats.dsa_practice.ai_generated,
                  }
                : null
            }
          />

          <ModuleCard
            title="Project Challenge"
            total={projectTotal}
            average={projectAverage}
            description="Mini project and hackathon-style challenges for ML, Analytics, DSA, and System Design."
          />

          <ModuleCard
            title="Voice Interview"
            total={interviewTotal}
            average={interviewAverage}
            description="Real-time spoken mock interview with follow-ups, scoring, and final report."
          />
        </div>

        <div className="mb-8 grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <SectionCard title="Recent Activity Timeline">
              {activityTimeline.length > 0 ? (
                <div className="space-y-3">
                  {activityTimeline.map((item) => {
                    const tone = getScoreTone(item.score);

                    return (
                      <div
                        key={item.id}
                        className="rounded-xl border border-slate-700 bg-slate-950/50 p-4"
                      >
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-widest text-cyan-300">
                              {item.type}
                            </p>
                            <p className="mt-1 font-semibold text-white">
                              {item.title}
                            </p>
                            <p className="mt-1 text-sm leading-6 text-slate-400">
                              {item.subtitle}
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {formatDate(item.created_at)}
                            </p>
                          </div>

                          <span
                            className={`rounded-full border ${tone.border} px-3 py-1 text-xs font-semibold ${tone.text}`}
                          >
                            {item.score}/10
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyBox
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
                  <div
                    key={item.topic}
                    className="rounded-xl border border-slate-700 bg-slate-950/50 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-white">
                          {item.topic}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {item.attempts} attempt(s) · {item.types}
                        </p>
                      </div>

                      <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-200">
                        {item.readiness}%
                      </span>
                    </div>

                    <ProgressBar value={item.readiness} />

                    <p className="mt-2 text-xs text-slate-400">
                      Avg Score: {item.averageScore}/10
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyBox
                title="No topic data yet"
                message="Practice any topic and it will appear here."
              />
            )}
          </SectionCard>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <SectionCard title="Recent ML Practice">
            {mlPractice.length > 0 ? (
              <div className="space-y-3">
                {mlPractice.slice(0, 8).map((item) => (
                  <CompactRecord
                    key={`ml-${item.id}`}
                    title={item.topic || "ML Practice"}
                    subtitle={`Score: ${item.score}/10 · Verdict: ${
                      item.verdict || "PARTIAL"
                    }`}
                    date={item.created_at}
                  />
                ))}
              </div>
            ) : (
              <EmptyBox title="No ML practice saved" />
            )}
          </SectionCard>

          <SectionCard title="Recent DSA Attempts">
            {dsaPractice.length > 0 ? (
              <div className="space-y-3">
                {dsaPractice.slice(0, 8).map((item) => (
                  <CompactRecord
                    key={`dsa-${item.id}`}
                    title={item.problem_name || "DSA Problem"}
                    subtitle={`Topic: ${item.topic || "DSA"} · Score: ${
                      item.score
                    }/10 · Status: ${item.status || "Needs Improvement"}`}
                    date={item.created_at}
                  />
                ))}
              </div>
            ) : (
              <EmptyBox title="No DSA attempt saved" />
            )}
          </SectionCard>

          <SectionCard title="Recent Project Challenges">
            {projectChallenge.length > 0 ? (
              <div className="space-y-3">
                {projectChallenge.slice(0, 8).map((item) => (
                  <CompactRecord
                    key={`project-${item.id}`}
                    title={item.project_title || "Project Challenge"}
                    subtitle={`Domain: ${item.domain || "N/A"} · Topic: ${
                      item.topic || "Project"
                    } · Score: ${item.score}/10 · Verdict: ${
                      item.verdict || "PARTIAL"
                    }`}
                    date={item.created_at}
                  />
                ))}
              </div>
            ) : (
              <EmptyBox title="No project challenge saved" />
            )}
          </SectionCard>

          <SectionCard title="Recent Voice Interviews">
            {voiceInterview.length > 0 ? (
              <div className="space-y-3">
                {voiceInterview.slice(0, 8).map((item) => (
                  <CompactRecord
                    key={`voice-${item.id}`}
                    title={item.topic || "Voice Interview"}
                    subtitle={`Rounds: ${item.rounds || 0} · Average Score: ${
                      item.average_score
                    }/10`}
                    date={item.created_at}
                  />
                ))}
              </div>
            ) : (
              <EmptyBox title="No voice interview saved" />
            )}
          </SectionCard>
        </div>
      </section>
    </main>
  );
}
