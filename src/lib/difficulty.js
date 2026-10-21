const STYLES = {
  Easy: { text: "text-emerald-300", badge: "bg-emerald-950/50 text-emerald-300", border: "border-l-emerald-400" },
  Medium: { text: "text-yellow-300", badge: "bg-yellow-950/50 text-yellow-300", border: "border-l-yellow-400" },
  Hard: { text: "text-red-300", badge: "bg-red-950/50 text-red-300", border: "border-l-red-400" },
};

const DEFAULT_STYLE = { text: "text-sky-300", badge: "bg-sky-950/50 text-sky-300", border: "border-l-sky-400" };

export function difficultyStyle(value) {
  return STYLES[value] || DEFAULT_STYLE;
}

export const DSA_TOPICS = [
  "Arrays",
  "Strings",
  "Linked List",
  "Stack",
  "Queue",
  "Binary Search",
  "Trees",
  "Graphs",
  "Dynamic Programming",
];
