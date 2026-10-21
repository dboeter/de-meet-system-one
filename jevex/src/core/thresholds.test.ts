import { describe, expect, it } from "vitest";
import { band } from "./thresholds.ts";

describe("band", () => {
  const t = { no: 0.2, yes: 0.8 };
  it.each([
    [0.95, "yes"],
    [0.8, "yes"],
    [0.79, "review"],
    [0.4, "review"],
    [0.21, "review"],
    [0.2, "no"],
    [0.02, "no"],
  ] as const)("p=%s → %s", (p, expected) => {
    expect(band(p, t)).toBe(expected);
  });

  it("collapses to a plain cut-off when no equals yes", () => {
    expect(band(0.5, { no: 0.5, yes: 0.5 })).toBe("yes");
    expect(band(0.49, { no: 0.5, yes: 0.5 })).toBe("no");
  });
});
