"use client";

import Editor from "@monaco-editor/react";
import { EmptyState } from "@/components/ui";

const EDITOR_OPTIONS = {
  fontSize: 14,
  fontFamily: "Consolas, 'Courier New', monospace",
  minimap: { enabled: false },
  tabSize: 4,
  insertSpaces: true,
  detectIndentation: false,
  automaticLayout: true,
  scrollBeyondLastLine: false,
  wordWrap: "on",
  lineNumbers: "on",
  cursorBlinking: "smooth",
  cursorSmoothCaretAnimation: "on",
  formatOnType: true,
  formatOnPaste: true,
  autoIndent: "full",
  bracketPairColorization: { enabled: true },
  guides: { indentation: true, bracketPairs: true },
  padding: { top: 16, bottom: 16 },
};

function defineTheme(_editor, monaco) {
  monaco.editor.defineTheme("conceptviva-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "", foreground: "E5E7EB", background: "0B1020" },
      { token: "comment", foreground: "94A3B8" },
      { token: "keyword", foreground: "C084FC" },
      { token: "number", foreground: "FBBF24" },
      { token: "string", foreground: "86EFAC" },
    ],
    colors: {
      "editor.background": "#0B1020",
      "editor.foreground": "#E5E7EB",
      "editorLineNumber.foreground": "#64748B",
      "editorCursor.foreground": "#FFFFFF",
      "editor.selectionBackground": "#334155",
      "editorIndentGuide.background": "#334155",
      "editorIndentGuide.activeBackground": "#64748B",
    },
  });
  monaco.editor.setTheme("conceptviva-dark");
}

export default function CodeEditor({ value, onChange, locked, lockedMessage }) {
  if (locked) {
    return <EmptyState className="min-h-[470px]" title="Code editor locked" message={lockedMessage} />;
  }
  return (
    <div className="overflow-hidden rounded-xl border border-slate-700 bg-[#0B1020]" data-testid="code-editor">
      <Editor
        height="470px"
        defaultLanguage="python"
        language="python"
        value={value}
        onChange={(next) => onChange(next || "")}
        onMount={defineTheme}
        options={EDITOR_OPTIONS}
        loading={<p className="p-4 text-sm text-slate-400">Loading editor...</p>}
      />
    </div>
  );
}
