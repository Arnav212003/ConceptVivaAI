import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import useLocalHistory from "@/hooks/useLocalHistory";
import { splitIntoSpeechChunks } from "@/hooks/useSpeechSynthesis";

describe("useLocalHistory", () => {
  it("persists, caps and clears entries", () => {
    const { result } = renderHook(() => useLocalHistory("test_history", 2));
    act(() => result.current.add({ topic: "A" }));
    act(() => result.current.add({ topic: "B" }));
    act(() => result.current.add({ topic: "C" }));

    expect(result.current.items.map((item) => item.topic)).toEqual(["C", "B"]);
    expect(JSON.parse(window.localStorage.getItem("test_history"))).toHaveLength(2);

    act(() => result.current.clear());
    expect(result.current.items).toEqual([]);
    expect(window.localStorage.getItem("test_history")).toBeNull();
  });

  it("survives corrupted storage", () => {
    window.localStorage.setItem("broken_history", "{not json");
    const { result } = renderHook(() => useLocalHistory("broken_history"));
    expect(result.current.items).toEqual([]);
  });
});

describe("speech chunking", () => {
  it("splits on sentence boundaries including the Hindi danda", () => {
    expect(splitIntoSpeechChunks("Use a map. Then loop! Done? हाँ। ठीक")).toEqual([
      "Use a map.",
      "Then loop!",
      "Done?",
      "हाँ।",
      "ठीक",
    ]);
    expect(splitIntoSpeechChunks("")).toEqual([]);
  });
});
