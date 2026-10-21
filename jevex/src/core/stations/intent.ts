import { choiceOf, ranked, type JevResponse } from "../jev.ts";
import { firstMatch, type RegexRule, type Span } from "../regex.ts";
import { wordingEntry, type Wording } from "../wording.ts";
import { readText, type StationDef } from "./station.ts";

export const INTENTS = ["refund", "exchange", "cancel", "complaint", "question", "praise", "other"] as const;
export type Intent = (typeof INTENTS)[number];

export type IntentPreset = { readonly id: string; readonly label: string; readonly text: string; readonly gold: Intent; readonly note: string };

const DEFAULT_RULES = String.raw`refund: /\b(refund|money back|reimburs\w*)\b/i
cancel: /\b(cancel|unsubscribe|close my account)\b/i
complaint: /\b(broken|damaged|terrible|worst|unacceptable|useless|complain\w*)\b/i
question: /\?\s*$|\b(how|when|where|can i|do you)\b/i
praise: /\b(thanks|thank you|love|great)\b/i`;

const DEFAULT_WORDING = {
  intent: {
    instructions: "What does the customer want from this email?",
    criteria: {
      refund: "Wants money back now, for a purchase",
      exchange: "Wants a replacement, a repair or a different item, not money back",
      cancel: "Wants to stop a subscription, order or account",
      complaint: "Reports a problem or is unhappy, without asking for a specific remedy",
      question: "Asks for information, including whether a refund, return or other remedy is possible; nothing is requested yet",
      praise: "Thanks or compliments; no action needed",
      other: "None of the above",
    },
  },
} satisfies Wording;

// Non-empty: each screen opens on its first preset.
const PRESETS: readonly [IntentPreset, ...IntentPreset[]] = [
  { id: "came-through", label: "Refund came through", text: "The refund came through yesterday, thanks!", gold: "praise", note: "Past tense: the refund already happened, nothing to do." },
  { id: "money-back", label: "Give me back what I paid", text: "Give me back what I paid, this thing is useless.", gold: "refund", note: "A refund request without the word refund." },
  { id: "negation", label: "Don't want a refund", text: "I don't want a refund, just send one that works.", gold: "exchange", note: "Negation: the keyword is there, the intent is the opposite." },
  { id: "sarcasm", label: "Sarcasm", text: "Great, thanks for shipping it to the wrong city.", gold: "complaint", note: "Sarcasm: every keyword is positive." },
  { id: "policy", label: "Policy question", text: "Can I get my money back if it's still sealed?", gold: "question", note: "Asks about the policy; no request yet." },
  { id: "dont-cancel", label: "Don't cancel", text: "Please don't cancel my subscription, I only wanted to know when it renews.", gold: "question", note: "Negation again, with a different keyword." },
  { id: "typo", label: "Typo", text: "pls refnd order 4471", gold: "refund", note: "Misspelling: the pattern needs the exact word." },
];

export type IntentRegexVerdict = { readonly label: string; readonly span: Span | null };

/** Run the keyword ladder; first rule that matches wins, otherwise `none`. */
export function intentRegexVerdict(rules: readonly RegexRule[], text: string): IntentRegexVerdict {
  const hit = firstMatch(rules, text);
  return hit ? { label: hit.label, span: hit.span } : { label: "none", span: null };
}

export type IntentReading = {
  readonly label: string;
  readonly confidence: number;
  readonly ranked: readonly { readonly label: string; readonly p: number }[];
};

export function readIntent(response: JevResponse): IntentReading {
  const answer = choiceOf(response, "intent");
  return { label: answer.choice, confidence: answer.confidence, ranked: ranked(answer) };
}

export const intent = {
  id: "intent",
  defaultRules: DEFAULT_RULES,
  defaultWording: DEFAULT_WORDING,
  presets: PRESETS,
  presetInputs: PRESETS.map((p) => ({ text: p.text })),
  build({ raw, wording, model }) {
    const t = readText(raw);
    if (t.kind === "error") return t;
    const w = wordingEntry(wording, DEFAULT_WORDING, "intent");
    return {
      kind: "ok",
      request: {
        model,
        state: t.text,
        questions: { intent: { type: "choice", instructions: w.instructions, criteria: w.criteria ?? {} } },
      },
    };
  },
} as const satisfies StationDef & Record<string, unknown>;
