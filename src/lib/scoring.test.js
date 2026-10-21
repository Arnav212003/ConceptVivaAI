import { describe, expect, it } from "vitest";
import { averageScore, formatScore, isScored, scoreTone } from "@/lib/scoring";

describe("scoring helpers", () => {
  it("never formats a missing score as 0", () => {
    expect(formatScore(null)).toBe("Not scored");
    expect(formatScore(undefined)).toBe("Not scored");
    expect(formatScore(0)).toBe("0/10");
    expect(formatScore(7.25)).toBe("7.3/10");
  });

  it("treats unavailable evaluations as unscored even with a numeric score", () => {
    expect(isScored({ evaluation_status: "completed", score: 8 })).toBe(true);
    expect(isScored({ evaluation_status: "unavailable", score: null })).toBe(false);
    expect(isScored({ evaluation_status: "unavailable", score: 5 })).toBe(false);
  });

  it("averages only real scores", () => {
    expect(averageScore([{ score: 8 }, { score: null }, { score: 6 }])).toBe(7);
    expect(averageScore([{ score: null }])).toBeNull();
  });

  it("uses a neutral tone for unscored results", () => {
    expect(scoreTone(null).text).toBe("text-slate-300");
    expect(scoreTone(9).text).toBe("text-emerald-300");
  });
});
