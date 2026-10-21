/**
 * The request and response shapes this demo sends to and reads from Jev, as plain JSON.
 * Station modules build these without importing the SDK, so the browser bundle never
 * pulls in the client; only the server and scripts hand them to `TypeSafeClient`.
 */

import { isRecord } from "./guards.ts";

export type Json = string | number | boolean | null | readonly Json[] | { readonly [key: string]: Json };

export type ChoiceQuestion = {
  readonly type: "choice";
  readonly instructions: string;
  readonly criteria: Readonly<Record<string, string | null>>;
};
export type NoulQuestion = {
  readonly type: "noul";
  readonly instructions: string;
};
export type ScoreQuestion = {
  readonly type: "score";
  readonly instructions: string;
  readonly criteria: readonly [string, string, ...string[]];
};
export type Question = ChoiceQuestion | NoulQuestion | ScoreQuestion;
export type Questions = Readonly<Record<string, Question>>;

export type JevRequest = {
  readonly model: string;
  readonly state: Json;
  readonly questions: Questions;
};

export type ChoiceAnswer = {
  readonly type: "choice";
  readonly choice: string;
  readonly confidence: number;
  readonly probabilities: Readonly<Record<string, number>>;
};
export type NoulAnswer = { readonly type: "noul"; readonly noul: number };
export type ScoreAnswer = {
  readonly type: "score";
  readonly score: number;
  readonly confidence: number;
  readonly probabilities: Readonly<Record<string, number>>;
};
export type Answer = ChoiceAnswer | NoulAnswer | ScoreAnswer;

export type JevResponse = {
  readonly model: string;
  readonly answers: Readonly<Record<string, Answer>>;
  readonly usage: { readonly input_tokens: number | null; readonly output_tokens: number | null };
};

function isNumberRecord(v: unknown): v is Record<string, number> {
  return isRecord(v) && Object.values(v).every((x) => typeof x === "number");
}

function parseAnswer(v: unknown): Answer | null {
  if (!isRecord(v)) return null;
  switch (v.type) {
    case "noul":
      return typeof v.noul === "number" ? { type: "noul", noul: v.noul } : null;
    case "choice":
      return typeof v.choice === "string" && typeof v.confidence === "number" && isNumberRecord(v.probabilities)
        ? { type: "choice", choice: v.choice, confidence: v.confidence, probabilities: v.probabilities }
        : null;
    case "score":
      return typeof v.score === "number" && typeof v.confidence === "number" && isNumberRecord(v.probabilities)
        ? { type: "score", score: v.score, confidence: v.confidence, probabilities: v.probabilities }
        : null;
    default:
      return null;
  }
}

/** Validate a response that crossed a boundary (API, server, recordings file). */
export function parseJevResponse(v: unknown): JevResponse | null {
  if (!isRecord(v) || typeof v.model !== "string" || !isRecord(v.answers) || !isRecord(v.usage)) return null;
  const answers: Record<string, Answer> = {};
  for (const [id, raw] of Object.entries(v.answers)) {
    const answer = parseAnswer(raw);
    if (!answer) return null;
    answers[id] = answer;
  }
  const tokens = (x: unknown): number | null => (typeof x === "number" ? x : null);
  return {
    model: v.model,
    answers,
    usage: { input_tokens: tokens(v.usage.input_tokens), output_tokens: tokens(v.usage.output_tokens) },
  };
}

function parseQuestion(v: unknown): Question | null {
  if (!isRecord(v) || typeof v.instructions !== "string") return null;
  switch (v.type) {
    case "noul":
      return { type: "noul", instructions: v.instructions };
    case "choice":
      return isRecord(v.criteria) && Object.values(v.criteria).every((d) => d === null || typeof d === "string")
        ? { type: "choice", instructions: v.instructions, criteria: v.criteria as Record<string, string | null> }
        : null;
    case "score": {
      const c = v.criteria;
      return Array.isArray(c) && c.length >= 2 && c.every((d) => typeof d === "string")
        ? { type: "score", instructions: v.instructions, criteria: c as [string, string, ...string[]] }
        : null;
    }
    default:
      return null;
  }
}

function isJson(v: unknown): v is Json {
  if (v === null || typeof v === "string" || typeof v === "number" || typeof v === "boolean") return true;
  if (Array.isArray(v)) return v.every(isJson);
  return isRecord(v) && Object.values(v).every(isJson);
}

/** Validate a request that crossed a boundary (server reply, recordings file). */
export function parseJevRequest(v: unknown): JevRequest | null {
  if (!isRecord(v) || typeof v.model !== "string" || !isRecord(v.questions) || !isJson(v.state)) return null;
  const questions: Record<string, Question> = {};
  for (const [id, raw] of Object.entries(v.questions)) {
    const q = parseQuestion(raw);
    if (!q) return null;
    questions[id] = q;
  }
  return { model: v.model, state: v.state, questions };
}

export class MissingAnswerError extends Error {
  override name = "MissingAnswerError";
}

function answerOf<T extends Answer["type"]>(
  response: JevResponse,
  id: string,
  type: T,
): Extract<Answer, { type: T }> {
  const answer = response.answers[id];
  if (!answer || answer.type !== type) throw new MissingAnswerError(`No ${type} answer for "${id}"`);
  // Narrowed by the `type` check above; TypeScript cannot relate the generic to the union.
  return answer as Extract<Answer, { type: T }>;
}

export const choiceOf = (r: JevResponse, id: string): ChoiceAnswer => answerOf(r, id, "choice");
export const noulOf = (r: JevResponse, id: string): NoulAnswer => answerOf(r, id, "noul");
export const scoreOf = (r: JevResponse, id: string): ScoreAnswer => answerOf(r, id, "score");

/** Options of a Choice answer, most probable first. */
export function ranked(answer: ChoiceAnswer): readonly { readonly label: string; readonly p: number }[] {
  return Object.entries(answer.probabilities)
    .map(([label, p]) => ({ label, p }))
    .sort((a, b) => b.p - a.p);
}
