import { describe, expect, it } from "vitest";
import { findAll, firstMatch, formatRules, parseRules } from "./regex.ts";

describe("parseRules", () => {
  it("parses one `label: /source/flags` rule per line, skipping blank lines", () => {
    const parsed = parseRules("refund: /\\brefund\\b/i\n\npraise: /thanks/");
    expect(parsed.kind).toBe("ok");
    if (parsed.kind !== "ok") return;
    expect(parsed.rules.map((r) => [r.label, r.source, r.flags])).toEqual([
      ["refund", "\\brefund\\b", "i"],
      ["praise", "thanks", ""],
    ]);
  });

  it("reports the line number of a malformed rule", () => {
    expect(parseRules("refund: /ok/i\nno slashes here")).toEqual({
      kind: "error",
      line: 2,
      message: "Expected `label: /pattern/flags`",
    });
  });

  it("reports an invalid pattern instead of throwing", () => {
    const parsed = parseRules("bad: /(unclosed/");
    expect(parsed.kind).toBe("error");
  });

  it("round-trips through formatRules", () => {
    const text = "a: /x|y/i\nb: /\\d+/";
    const parsed = parseRules(text);
    if (parsed.kind !== "ok") throw new Error("expected ok");
    expect(formatRules(parsed.rules)).toBe(text);
  });
});

describe("firstMatch", () => {
  it("returns the first rule in order that matches, with the matched span", () => {
    const parsed = parseRules("refund: /refund/i\npraise: /thanks/i");
    if (parsed.kind !== "ok") throw new Error("expected ok");
    expect(firstMatch(parsed.rules, "Thanks, the refund came")).toEqual({
      label: "refund",
      span: { start: 12, end: 18, text: "refund" },
    });
    expect(firstMatch(parsed.rules, "nothing here")).toBeNull();
  });
});

describe("findAll", () => {
  it("finds every match span, even for a non-global pattern", () => {
    expect(findAll(/A-\d+/, "A-1 and A-22")).toEqual([
      { start: 0, end: 3, text: "A-1" },
      { start: 8, end: 12, text: "A-22" },
    ]);
  });
});
