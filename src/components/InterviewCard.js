"use client";

import { useEffect, useRef, useState } from "react";
import ResultCard from "./ResultCard";

export default function InterviewCard() {
  const [topic, setTopic] = useState("Linear Regression");
  const [level, setLevel] = useState("Easy");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [loadingEvaluation, setLoadingEvaluation] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [autoMode, setAutoMode] = useState(false);
  const [round, setRound] = useState(0);
  const [interviewScores, setInterviewScores] = useState([]);
  const [interviewHistory, setInterviewHistory] = useState([]);
  const [finalReport, setFinalReport] = useState(null);

  const recognitionRef = useRef(null);
  const keepListeningRef = useRef(false);
  const transcriptRef = useRef("");
  const maxRounds = 5;
  

  useEffect(() => {
    const savedHistory = localStorage.getItem("conceptviva_interview_history");

    if (savedHistory) {
      setInterviewHistory(JSON.parse(savedHistory));
    }
  }, []);

  function getSpeechRecognition() {
    if (typeof window === "undefined") return null;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) return null;

    return new SpeechRecognition();
  }

  function speakText(text, afterSpeak) {
    if (typeof window === "undefined") return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = 0.95;
    utterance.pitch = 1;

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);

      if (afterSpeak) {
        afterSpeak();
      }
    };

    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    if (typeof window !== "undefined") {
      window.speechSynthesis.cancel();
    }

    setIsSpeaking(false);
  }

  function startListening() {
  const recognition = getSpeechRecognition();

  if (!recognition) {
    alert("Speech recognition is not supported in this browser. Use Chrome or Edge.");
    return;
  }

  stopSpeaking();

  if (recognitionRef.current) {
    try {
      recognitionRef.current.stop();
    } catch (error) {}
  }

  keepListeningRef.current = true;
  transcriptRef.current = answer ? `${answer.trim()} ` : "";

  recognitionRef.current = recognition;

  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  recognition.onstart = () => {
    setIsListening(true);
  };

  recognition.onresult = (event) => {
    let finalText = "";
    let interimText = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const spokenText = event.results[i][0].transcript;

      if (event.results[i].isFinal) {
        finalText += `${spokenText} `;
      } else {
        interimText += spokenText;
      }
    }

    if (finalText.trim()) {
      transcriptRef.current += finalText;
    }

    setAnswer((transcriptRef.current + interimText).trim());
  };

  recognition.onerror = (event) => {
    console.log("Speech recognition error:", event.error);

    if (
      event.error === "not-allowed" ||
      event.error === "service-not-allowed"
    ) {
      keepListeningRef.current = false;
      setIsListening(false);
      alert("Microphone permission is blocked. Please allow microphone permission.");
    }
  };

  recognition.onend = () => {
    if (keepListeningRef.current) {
      setTimeout(() => {
        try {
          recognition.start();
        } catch (error) {}
      }, 300);
    } else {
      setIsListening(false);
    }
  };

  try {
    recognition.start();
  } catch (error) {
    console.log("Mic start error:", error);
  }
}

  function stopListening() {
  keepListeningRef.current = false;

  if (recognitionRef.current) {
    try {
      recognitionRef.current.stop();
    } catch (error) {}
  }

  setIsListening(false);
}

  function resetInterview() {
    stopSpeaking();
    stopListening();

    setQuestion("");
    setAnswer("");
    setResult(null);
    setRound(0);
    setInterviewScores([]);
    setFinalReport(null);
    setAutoMode(false);
  }

  function getAverageScore(scores) {
    if (!scores.length) return 0;

    const total = scores.reduce((sum, item) => sum + Number(item.score || 0), 0);
    return Number((total / scores.length).toFixed(1));
  }

  function getInterviewRecommendation(avgScore) {
    if (avgScore >= 8) {
      return "Strong interview performance. You are close to interview-ready for this topic.";
    }

    if (avgScore >= 6) {
      return "Good base is present, but answers need more structure, examples, and technical depth.";
    }

    return "Needs focused revision. First revise core concepts, then practice short structured answers.";
  }

  function getStrongPoints(avgScore) {
    if (avgScore >= 8) {
      return "Concept clarity, confidence, and answer structure look strong.";
    }

    if (avgScore >= 6) {
      return "Basic understanding is present and you are able to attempt the questions.";
    }

    return "You are practicing consistently, which is the first strong point.";
  }

  function getWeakPoints(avgScore) {
    if (avgScore >= 8) {
      return "Add more real-world examples and edge-case explanations to make answers stronger.";
    }

    if (avgScore >= 6) {
      return "Improve depth, examples, interview keywords, and step-by-step explanation.";
    }

    return "Revise definitions, working, examples, advantages, limitations, and common interview questions.";
  }

  function saveInterviewReport(scores) {
    const avgScore = getAverageScore(scores);
    const today = new Date();

    const report = {
      id: Date.now(),
      date: today.toLocaleDateString(),
      time: today.toLocaleTimeString(),
      topic,
      level,
      rounds: scores.length,
      averageScore: avgScore,
      strongPoints: getStrongPoints(avgScore),
      weakPoints: getWeakPoints(avgScore),
      recommendation: getInterviewRecommendation(avgScore),
    };

    const updatedHistory = [report, ...interviewHistory].slice(0, 20);

    setFinalReport(report);
    setInterviewHistory(updatedHistory);
    localStorage.setItem(
      "conceptviva_interview_history",
      JSON.stringify(updatedHistory)
    );
  }

  function clearInterviewHistory() {
    setInterviewHistory([]);
    localStorage.removeItem("conceptviva_interview_history");
  }

  async function generateQuestion(customQuestion = "") {
    setLoadingQuestion(true);
    setResult(null);
    setAnswer("");

    try {
      if (customQuestion) {
        setQuestion(customQuestion);
        setRound((prev) => prev + 1);

        speakText(customQuestion, () => {
          if (autoMode) {
            startListening();
          }
        });

        setLoadingQuestion(false);
        return;
      }

      const response = await fetch("/api/interview", {
        method: "POST",
        body: JSON.stringify({
          action: "question",
          topic,
          level,
        }),
      });

      const data = await response.json();

      const generatedQuestion =
        data.question || `Can you explain ${topic} clearly?`;

      setQuestion(generatedQuestion);
      setRound((prev) => prev + 1);

      speakText(generatedQuestion, () => {
        if (autoMode) {
          startListening();
        }
      });
    } catch (error) {
      const fallbackQuestion = `Can you explain the basic concept of ${topic}?`;
      setQuestion(fallbackQuestion);
      setRound((prev) => prev + 1);

      speakText(fallbackQuestion, () => {
        if (autoMode) {
          startListening();
        }
      });
    }

    setLoadingQuestion(false);
  }

  async function evaluateAnswer() {
    if (!question.trim()) {
      alert("Please generate a question first.");
      return;
    }

    if (!answer.trim()) {
      alert("Please speak or write your answer first.");
      return;
    }

    setLoadingEvaluation(true);

    try {
      const response = await fetch("/api/interview", {
        method: "POST",
        body: JSON.stringify({
          action: "evaluate",
          topic,
          level,
          question,
          answer,
        }),
      });

      const data = await response.json();

      const evaluation = {
        score: data.score ?? 0,
        feedback: data.feedback || "No feedback received.",
        improvement: data.improvement || "Improve answer structure.",
        follow_up_question:
          data.follow_up_question ||
          `Can you explain one practical use case of ${topic}?`,
      };

      setResult(evaluation);

      const updatedScores = [
        ...interviewScores,
        {
          round,
          score: Number(evaluation.score || 0),
          question,
          answer,
        },
      ];

      setInterviewScores(updatedScores);

      const shortFeedback = `Your score is ${evaluation.score} out of 10. ${evaluation.improvement}`;

      speakText(shortFeedback, () => {
        if (autoMode) {
          if (updatedScores.length >= maxRounds) {
            saveInterviewReport(updatedScores);
            setAutoMode(false);
          } else {
            generateQuestion(evaluation.follow_up_question);
          }
        }
      });
    } catch (error) {
      const evaluation = {
        score: 5,
        feedback: "Something went wrong while evaluating your answer.",
        improvement: "Check backend and API route connection.",
        follow_up_question: `Can you explain ${topic} with an example?`,
      };

      setResult(evaluation);

      const updatedScores = [
        ...interviewScores,
        {
          round,
          score: Number(evaluation.score || 0),
          question,
          answer,
        },
      ];

      setInterviewScores(updatedScores);

      speakText("Evaluation failed. Please check backend connection.");
    }

    setLoadingEvaluation(false);
  }

  function startAutoInterview() {
    resetInterview();
    setAutoMode(true);

    setTimeout(() => {
      generateQuestion();
    }, 300);
  }

  function finishInterviewNow() {
    if (interviewScores.length === 0) {
      alert("No evaluated answer yet. Answer at least one question first.");
      return;
    }

    saveInterviewReport(interviewScores);
    setAutoMode(false);
    stopSpeaking();
    stopListening();
  }

  const totalInterviews = interviewHistory.length;

  const averageInterviewScore =
    totalInterviews > 0
      ? (
          interviewHistory.reduce(
            (sum, item) => sum + Number(item.averageScore || 0),
            0
          ) / totalInterviews
        ).toFixed(1)
      : "0.0";

  const lastInterviewTopic = interviewHistory[0]?.topic || "N/A";

  return (
    <div className="mt-10 w-full max-w-6xl rounded-3xl border border-slate-700 bg-slate-950/70 p-5 shadow-2xl">
      <div className="mb-6 flex flex-col gap-4 border-b border-slate-800 pb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-cyan-300">
            Voice Interview Mode
          </p>

          <h2 className="mt-2 text-3xl font-bold text-white">
            AI Mock Interview Coach
          </h2>

          <p className="mt-1 text-base text-slate-400">
            Practice topic-wise interview questions with voice, evaluation,
            follow-ups, and final performance report.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={startAutoInterview}
            disabled={loadingQuestion || loadingEvaluation}
            className="rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-cyan-600 disabled:opacity-60"
          >
            Start Auto Interview
          </button>

          <button
            onClick={finishInterviewNow}
            className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-600"
          >
            Finish & Report
          </button>

          <button
            onClick={resetInterview}
            className="rounded-xl bg-slate-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-600"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Total Interviews</p>
          <p className="mt-1 text-3xl font-bold text-white">
            {totalInterviews}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Avg Interview Score</p>
          <p className="mt-1 text-3xl font-bold text-white">
            {averageInterviewScore}/10
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Current Round</p>
          <p className="mt-1 text-3xl font-bold text-white">
            {round}/{maxRounds}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Last Topic</p>
          <p className="mt-1 text-xl font-bold text-white">
            {lastInterviewTopic}
          </p>
        </div>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-2 block text-sm text-slate-300">
            Interview Topic
          </label>

          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
            placeholder="Example: Linear Regression"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm text-slate-300">
            Difficulty
          </label>

          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
          >
            <option>Easy</option>
            <option>Medium</option>
            <option>Hard</option>
          </select>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold text-white">Question</h3>
              <p className="text-sm text-slate-400">
                AI interviewer will ask one question at a time.
              </p>
            </div>

            <button
              onClick={() => generateQuestion()}
              disabled={loadingQuestion}
              className="rounded-xl bg-pink-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-pink-600 disabled:opacity-60"
            >
              {loadingQuestion ? "Generating..." : "Generate Question"}
            </button>
          </div>

          <div className="min-h-[180px] rounded-xl border border-slate-700 bg-slate-950/60 p-5">
            {question ? (
              <p className="whitespace-pre-line text-lg leading-8 text-white">
                {question}
              </p>
            ) : (
              <p className="text-slate-400">
                No question yet. Click Generate Question or Start Auto
                Interview.
              </p>
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={() => speakText(question)}
              disabled={!question || isSpeaking}
              className="rounded-xl bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-600 disabled:opacity-60"
            >
              {isSpeaking ? "Speaking..." : "Speak Question"}
            </button>

            <button
              onClick={stopSpeaking}
              className="rounded-xl bg-slate-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-600"
            >
              Stop Voice
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold text-white">Your Answer</h3>
              <p className="text-sm text-slate-400">
                Speak or type your answer, then submit for evaluation.
              </p>
            </div>

            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                isListening
                  ? "bg-red-950/50 text-red-300"
                  : "bg-slate-800 text-slate-300"
              }`}
            >
              {isListening ? "Listening..." : "Mic Idle"}
            </span>
          </div>

          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            className="min-h-[180px] w-full rounded-xl border border-slate-700 bg-slate-950/60 p-4 text-base leading-7 text-white outline-none"
            placeholder="Your answer will appear here..."
          />

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={startListening}
              disabled={isListening}
              className="rounded-xl bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-60"
            >
              Start Mic
            </button>

            <button
              onClick={stopListening}
              className="rounded-xl bg-slate-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-600"
            >
              Stop Mic
            </button>

            <button
              onClick={evaluateAnswer}
              disabled={loadingEvaluation}
              className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
            >
              {loadingEvaluation ? "Evaluating..." : "Evaluate Answer"}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <div className="mt-6">
          <ResultCard result={result} />
        </div>
      )}

      {finalReport && (
        <div className="mt-8 rounded-2xl border border-emerald-400/30 bg-emerald-950/20 p-5">
          <h3 className="text-2xl font-bold text-white">
            Final Interview Report
          </h3>

          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-400">Topic</p>
              <p className="mt-1 font-bold text-white">{finalReport.topic}</p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-400">Rounds</p>
              <p className="mt-1 font-bold text-white">
                {finalReport.rounds}
              </p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-400">Average Score</p>
              <p className="mt-1 font-bold text-white">
                {finalReport.averageScore}/10
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="font-semibold text-emerald-300">Strong Points</p>
              <p className="mt-2 text-sm leading-7 text-slate-200">
                {finalReport.strongPoints}
              </p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="font-semibold text-yellow-300">Weak Points</p>
              <p className="mt-2 text-sm leading-7 text-slate-200">
                {finalReport.weakPoints}
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-xl border border-cyan-400/30 bg-cyan-950/20 p-4">
            <p className="font-semibold text-cyan-300">Final Recommendation</p>
            <p className="mt-2 text-sm leading-7 text-slate-200">
              {finalReport.recommendation}
            </p>
          </div>
        </div>
      )}

      <div className="mt-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-white">
              Recent Interview History
            </h3>
            <p className="text-sm text-slate-400">
              Your latest interview reports are saved in this browser.
            </p>
          </div>

          <button
            onClick={clearInterviewHistory}
            disabled={interviewHistory.length === 0}
            className="rounded-xl bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-50"
          >
            Clear History
          </button>
        </div>

        {interviewHistory.length > 0 ? (
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-700">
                  <th className="py-3 pr-3">Date</th>
                  <th className="py-3 pr-3">Topic</th>
                  <th className="py-3 pr-3">Difficulty</th>
                  <th className="py-3 pr-3">Rounds</th>
                  <th className="py-3 pr-3">Avg Score</th>
                  <th className="py-3 pr-3">Recommendation</th>
                </tr>
              </thead>

              <tbody>
                {interviewHistory.map((item) => (
                  <tr key={item.id} className="border-b border-slate-800">
                    <td className="py-3 pr-3 text-slate-300">
                      {item.date} {item.time}
                    </td>
                    <td className="py-3 pr-3 font-semibold text-white">
                      {item.topic}
                    </td>
                    <td className="py-3 pr-3 text-slate-300">{item.level}</td>
                    <td className="py-3 pr-3 text-slate-300">
                      {item.rounds}
                    </td>
                    <td className="py-3 pr-3 font-bold text-white">
                      {item.averageScore}/10
                    </td>
                    <td className="py-3 pr-3 text-slate-300">
                      {item.recommendation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center">
            <p className="font-semibold text-white">
              No interview history yet
            </p>
            <p className="mt-2 text-sm text-slate-400">
              Complete an interview and click Finish & Report to save it.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}