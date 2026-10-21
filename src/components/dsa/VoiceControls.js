export default function VoiceControls({ voice, large = false }) {
  const size = large ? "px-6 py-4 text-base" : "px-3 py-1.5 text-xs";

  let button;
  if (voice.translating) {
    button = (
      <button disabled className={`rounded-xl bg-indigo-950/60 font-semibold text-indigo-300 ${size}`}>
        {large ? "Translating to Hindi..." : "Translating..."}
      </button>
    );
  } else if (voice.isSpeaking) {
    button = (
      <button onClick={voice.stop} className={`rounded-xl bg-red-600 font-semibold text-white hover:bg-red-700 ${size}`}>
        ⏹ {large ? "Stop AI Explanation" : "Stop"}
      </button>
    );
  } else {
    button = (
      <button
        onClick={() => voice.explain()}
        className={`rounded-xl bg-indigo-500 font-semibold text-white hover:bg-indigo-600 ${size}`}
      >
        🔊 {large ? "Have AI Explain This Out Loud" : "Explain via Voice"}
      </button>
    );
  }

  return (
    <div className={`flex flex-wrap items-center gap-2 ${large ? "flex-col" : ""}`}>
      <div className="flex gap-2" role="group" aria-label="Explanation language">
        {[
          ["en", "English"],
          ["hi", "हिंदी"],
        ].map(([code, label]) => (
          <button
            key={code}
            onClick={() => voice.setLanguage(code)}
            aria-pressed={voice.language === code}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              voice.language === code ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {button}
    </div>
  );
}
