"use client";

import { useCallback, useEffect, useRef, useState } from "react";

function createRecognition() {
  if (typeof window === "undefined") return null;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  return SpeechRecognition ? new SpeechRecognition() : null;
}

// Continuous dictation that restarts itself when the browser ends a session
// mid-answer. `onTranscript` receives the full transcript (final + interim).
export default function useSpeechRecognition({ onTranscript, lang = "en-US" } = {}) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState("");
  const recognitionRef = useRef(null);
  const keepListeningRef = useRef(false);
  const transcriptRef = useRef("");
  const onTranscriptRef = useRef(onTranscript);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  const stop = useCallback(() => {
    keepListeningRef.current = false;
    try {
      recognitionRef.current?.stop();
    } catch {
      // already stopped
    }
    setIsListening(false);
  }, []);

  useEffect(() => stop, [stop]);

  const start = useCallback(
    (existingText = "") => {
      const recognition = createRecognition();
      if (!recognition) {
        setError("Speech recognition is not supported in this browser. Use Chrome or Edge, or type your answer.");
        return;
      }

      stop();
      setError("");
      keepListeningRef.current = true;
      transcriptRef.current = existingText ? `${existingText.trim()} ` : "";
      recognitionRef.current = recognition;
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => setIsListening(true);
      recognition.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const spoken = event.results[i][0].transcript;
          if (event.results[i].isFinal) transcriptRef.current += `${spoken} `;
          else interim += spoken;
        }
        onTranscriptRef.current?.((transcriptRef.current + interim).trim());
      };
      recognition.onerror = (event) => {
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          keepListeningRef.current = false;
          setIsListening(false);
          setError("Microphone permission is blocked. Allow microphone access in your browser settings.");
        }
      };
      recognition.onend = () => {
        if (keepListeningRef.current) {
          setTimeout(() => {
            try {
              recognition.start();
            } catch {
              // a new session may already be starting
            }
          }, 300);
        } else {
          setIsListening(false);
        }
      };

      try {
        recognition.start();
      } catch {
        setError("Could not start the microphone. Try again.");
      }
    },
    [lang, stop]
  );

  return { start, stop, isListening, error };
}
