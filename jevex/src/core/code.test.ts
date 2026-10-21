import { describe, expect, it } from "vitest";
import { sdkSnippet } from "./code.ts";
import type { JevRequest } from "./jev.ts";

describe("sdkSnippet", () => {
  it("is a runnable TypeScript SDK call carrying the exact request", () => {
    const request: JevRequest = {
      model: "jev-1.13.0",
      state: "it's \"broken\"",
      questions: { q: { type: "noul", instructions: "Is something broken?" } },
    };
    const code = sdkSnippet(request);
    expect(code).toContain('import { TypeSafeClient } from "@typesafe-ai/sdk";');
    expect(code).toContain("await client.systemOne(");
    const json = code.slice(code.indexOf("systemOne(") + "systemOne(".length, code.indexOf(");\nconsole.log"));
    expect(JSON.parse(json)).toEqual(request);
  });
});
