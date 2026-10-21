"use client";

import { useCallback, useEffect, useState } from "react";
import { apiPost } from "@/lib/api";
import useSpeechSynthesis from "@/hooks/useSpeechSynthesis";

// Reads the optimized approach + explanation aloud, in English or Hindi.
// Hindi text is translated once per solution and reused.
export default function useSolutionVoice(feedback) {
  const { speak, stop, isSpeaking } = useSpeechSynthesis();
  const [language, setLanguageState] = useState("en");
  const [hindiText, setHindiText] = useState("");
  const [translating, setTranslating] = useState(false);

  useEffect(() => {
    setHindiText("");
  }, [feedback]);

  const setLanguage = useCallback(
    (next) => {
      if (isSpeaking) stop();
      setLanguageState(next);
    },
    [isSpeaking, stop]
  );

  const explain = useCallback(
    async (source = feedback, lang = language) => {
      if (!source) return;
      const english = `${source.optimized_approach || ""}. ${source.explanation || ""}`;
      let text = english;

      if (lang === "hi") {
        if (hindiText) {
          text = hindiText;
        } else {
          setTranslating(true);
          try {
            const data = await apiPost("/api/dsa", {
              action: "translateHindi",
              text: `${source.optimized_approach || ""}\n\n${source.explanation || ""}`.slice(0, 8000),
            });
            text = data.translated_text || english;
            if (data.translated) setHindiText(text);
          } catch {
            text = english;
          } finally {
            setTranslating(false);
          }
        }
      }
      speak(text, { lang });
    },
    [feedback, hindiText, language, speak]
  );

  return { language, setLanguage, explain, stop, isSpeaking, translating };
}
