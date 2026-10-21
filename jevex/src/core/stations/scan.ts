import { noulOf, type JevResponse, type Questions } from "../jev.ts";
import { firstSpan, type RegexRule, type Span } from "../regex.ts";
import { wordingEntry, type Wording } from "../wording.ts";
import { readText, type BuildResult, type StationDef } from "./station.ts";

export type ScanPreset = { readonly id: string; readonly label: string; readonly text: string; readonly gold: readonly boolean[]; readonly note: string };

export const MAX_SENTENCES = 64;

const DEFAULT_RULES = String.raw`problem: /\b(wrong|broken|damaged|problem|issue|error|not working)\b/i`;

// `{i}` is replaced by the sentence index; the question points at the sentence by path so the
// whole email is still there as context.
const DEFAULT_WORDING = {
  needs_action: {
    instructions:
      "Does `sentences[{i}]` ask support for help, report a problem, or complain? A thank-you, praise, or an FYI that needs no action is not.",
  },
} satisfies Wording;

// Non-empty: each screen opens on its first preset.
const PRESETS: readonly [ScanPreset, ...ScanPreset[]] = [
  {
    id: "mixed",
    label: "A mixed ticket",
    text: "Thanks for the fast shipping last time! This order came with the wrong charger. Could you send the right one? FYI the tracking link in your email works now. Also, the app logs me out every ten minutes, which is driving me up the wall. Love the new colors, by the way.",
    gold: [false, true, true, false, true, false],
    note: "Six sentences, three need action; only one has a problem word.",
  },
  {
    id: "negated",
    label: "No problem at all",
    text: "Your new checkout is not a problem at all, it works great. However, my discount code SAVE10 was rejected twice. No issue with delivery though.",
    gold: [false, true, false],
    note: "The problem words are negated; the real problem has none.",
  },
];

/** Sentences with exact offsets into `text`, split on . ! ? and newlines. */
export function splitSentences(text: string): Span[] {
  const spans: Span[] = [];
  for (const m of text.matchAll(/[^.!?\n]+(?:[.!?]+|$)/gm)) {
    const raw = m[0];
    const lead = raw.length - raw.trimStart().length;
    const trimmed = raw.trim();
    if (trimmed === "") continue;
    const start = m.index + lead;
    spans.push({ start, end: start + trimmed.length, text: trimmed });
  }
  return spans;
}

export type ScanRegexHit = { readonly span: Span; readonly hit: Span | null };

export function scanRegex(rules: readonly RegexRule[], sentences: readonly Span[]): readonly ScanRegexHit[] {
  return sentences.map((span) => {
    for (const rule of rules) {
      const hit = firstSpan(rule.pattern, span.text);
      if (hit) return { span, hit: { start: span.start + hit.start, end: span.start + hit.end, text: hit.text } };
    }
    return { span, hit: null };
  });
}

export type ScanReading = { readonly span: Span; readonly p: number; readonly needsAction: boolean };

export function readScan(response: JevResponse, sentences: readonly Span[], threshold: number): readonly ScanReading[] {
  return sentences.map((span, i) => {
    const p = noulOf(response, `s${i}`).noul;
    return { span, p, needsAction: p >= threshold };
  });
}

function build(args: { raw: unknown; wording: Wording; model: string }): BuildResult {
  const t = readText(args.raw);
  if (t.kind === "error") return t;
  const sentences = splitSentences(t.text).map((s) => s.text);
  if (sentences.length > MAX_SENTENCES) {
    return { kind: "error", reason: "too_long", message: `More than ${MAX_SENTENCES} sentences` };
  }
  const template = wordingEntry(args.wording, DEFAULT_WORDING, "needs_action").instructions;
  const questions: Questions = Object.fromEntries(
    sentences.map((_, i) => [`s${i}`, { type: "noul", instructions: template.replaceAll("{i}", String(i)) }] as const),
  );
  return { kind: "ok", request: { model: args.model, state: { email: t.text, sentences }, questions } };
}

export const scan = {
  id: "scan",
  defaultRules: DEFAULT_RULES,
  defaultWording: DEFAULT_WORDING,
  defaultThreshold: 0.5,
  presets: PRESETS,
  presetInputs: PRESETS.map((p) => ({ text: p.text })),
  build,
} as const satisfies StationDef & Record<string, unknown>;
