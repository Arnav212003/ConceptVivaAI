"use client";

import { useCallback, useEffect, useState } from "react";

function readList(key) {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(key) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeList(key, items) {
  try {
    window.localStorage.setItem(key, JSON.stringify(items));
  } catch {
    // Storage can be full or blocked (private mode); history is a convenience only.
  }
}

// Browser-only quick history (the dashboard reads the real records from the backend).
export default function useLocalHistory(key, limit = 20) {
  const [items, setItems] = useState([]);

  useEffect(() => {
    setItems(readList(key));
  }, [key]);

  const add = useCallback(
    (entry) => {
      setItems((current) => {
        const updated = [{ id: Date.now(), ...entry }, ...current].slice(0, limit);
        writeList(key, updated);
        return updated;
      });
    },
    [key, limit]
  );

  const clear = useCallback(() => {
    setItems([]);
    try {
      window.localStorage.removeItem(key);
    } catch {
      // ignore
    }
  }, [key]);

  return { items, add, clear };
}
