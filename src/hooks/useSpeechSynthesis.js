"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Chrome cuts off long utterances after a few words, so text is spoken as a chain
// of sentence-sized chunks. `stop()` breaks the chain.
export function splitIntoSpeechChunks(text) {
  return String(text || "")
    .split(/(?<=[.!?।])\s+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
}

function hasSpeech() {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export default function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const stopRequestedRef = useRef(false);

  const stop = useCallback(() => {
    stopRequestedRef.current = true;
    if (hasSpeech()) window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  // Stop talking when the component using this hook unmounts (page navigation).
  useEffect(() => stop, [stop]);

  const speak = useCallback((text, { lang = "en", onEnd } = {}) => {
    if (!hasSpeech()) {
      onEnd?.();
      return;
    }

    stopRequestedRef.current = false;
    window.speechSynthesis.cancel();
    const chunks = splitIntoSpeechChunks(text);

    const speakAt = (index) => {
      if (stopRequestedRef.current || index >= chunks.length) {
        setIsSpeaking(false);
        if (!stopRequestedRef.current) onEnd?.();
        return;
      }
      const utterance = new SpeechSynthesisUtterance(chunks[index]);
      utterance.lang = lang === "hi" ? "hi-IN" : "en-US";
      utterance.rate = lang === "hi" ? 0.9 : 0.95;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => speakAt(index + 1);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    };

    speakAt(0);
  }, []);

  return { speak, stop, isSpeaking, supported: hasSpeech() };
}
