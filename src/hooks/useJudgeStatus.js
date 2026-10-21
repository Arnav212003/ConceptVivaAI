"use client";

import { useEffect, useState } from "react";

// null = unknown yet, so the UI does not claim either state before it knows.
export default function useJudgeStatus() {
  const [enabled, setEnabled] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/dsa?resource=bank-stats", { cache: "no-store" })
      .then((response) => response.json())
      .then((data) => {
        if (!cancelled) setEnabled(Boolean(data.hidden_tests_enabled));
      })
      .catch(() => {
        if (!cancelled) setEnabled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return enabled;
}
