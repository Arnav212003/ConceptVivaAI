const ERROR_KIND_LABEL = {
  syntax_error: "Syntax Error",
  signature_mismatch: "Function signature mismatch",
};

const VERDICT_STYLES = {
  Accepted: "border-emerald-400/40 bg-emerald-950/30 text-emerald-300",
  Pending: "border-slate-600 bg-slate-900/60 text-slate-300",
};

function statusColor(status) {
  const value = String(status || "").toLowerCase();
  if (value.includes("pass")) return "text-emerald-300 bg-emerald-950/40";
  if (value.includes("fail")) return "text-red-300 bg-red-950/40";
  return "text-yellow-300 bg-yellow-950/40";
}

// Prefer the judge's verdict; otherwise infer one from the returned test cases.
export function deriveVerdict(judge, testCases) {
  if (judge?.verdict) return judge.verdict;
  if (!Array.isArray(testCases) || testCases.length === 0) return null;
  const passed = testCases.filter((item) => String(item.status || "").toLowerCase().includes("pass")).length;
  return passed === testCases.length ? "Accepted" : "Wrong Answer";
}

export function VerdictBanner({ judge, testCases }) {
  const verdict = deriveVerdict(judge, testCases);
  if (!verdict) return null;

  const cases = Array.isArray(testCases) ? testCases : [];
  const passed = judge?.passed ?? cases.filter((c) => String(c.status || "").toLowerCase().includes("pass")).length;
  const total = judge?.total ?? cases.length;
  const style = VERDICT_STYLES[verdict] || "border-red-400/40 bg-red-950/30 text-red-300";

  return (
    <div className={`mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border px-5 py-4 ${style}`}>
      <div>
        <p className="text-lg font-bold" data-testid="verdict">{verdict}</p>
        {ERROR_KIND_LABEL[judge?.error_kind] && (
          <p className="text-sm font-semibold" data-testid="error-kind">{ERROR_KIND_LABEL[judge.error_kind]}</p>
        )}
        {total > 0 && (
          <p className="mt-1 text-xs text-slate-400">
            {passed} / {total} testcases passed
            {judge?.duration_ms ? ` · ${Math.round(judge.duration_ms)} ms` : ""}
          </p>
        )}
      </div>
      {judge?.error && verdict !== "Accepted" && (
        <pre className="max-w-full overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950/70 p-2 font-mono text-xs text-red-200">
          {judge.error}
        </pre>
      )}
    </div>
  );
}

export function TestCaseList({ testCases }) {
  if (!Array.isArray(testCases) || testCases.length === 0) {
    return <p className="text-sm text-slate-400">No test cases returned.</p>;
  }

  return (
    <div className="space-y-3">
      {testCases.map((item, index) => (
        <div key={index} className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="font-semibold text-white">Case {index + 1}</p>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusColor(item.status)}`}>
              {item.status || "Not Executed"}
            </span>
          </div>

          {item.hidden ? (
            <p className="text-xs text-slate-400">Hidden test. Inputs stay private so the judge can't be gamed.</p>
          ) : (
            <>
              {[
                ["Input", item.input],
                ["Expected Output", item.expected_output],
                ["Actual Output", item.actual_output || "N/A"],
              ].map(([label, value]) => (
                <div key={label}>
                  <p className="mt-3 text-xs text-slate-400 first:mt-0">{label}</p>
                  <pre className="mt-1 overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-3 font-mono text-xs text-slate-200">
                    {value}
                  </pre>
                </div>
              ))}
            </>
          )}
        </div>
      ))}
    </div>
  );
}
