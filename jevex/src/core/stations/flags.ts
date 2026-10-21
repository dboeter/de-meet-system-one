import { noulOf, type JevResponse, type Questions } from "../jev.ts";
import { firstSpan, type RegexRule, type Span } from "../regex.ts";
import { band, type Band, type BandThresholds } from "../thresholds.ts";
import { wordingEntry, type Wording } from "../wording.ts";
import { readText, type StationDef } from "./station.ts";

export const FLAGS = ["asks_refund_now", "wants_human", "repeat_contact", "legal_or_chargeback_threat", "cancellation_risk"] as const;
export type Flag = (typeof FLAGS)[number];
export type FlagGold = Readonly<Record<Flag, boolean>>;

export type FlagsPreset = { readonly id: string; readonly label: string; readonly text: string; readonly gold: FlagGold; readonly note: string };

const DEFAULT_RULES = String.raw`asks_refund_now: /\b(refund|money back)\b/i
wants_human: /\b(human|agent|real person|manager)\b/i
repeat_contact: /\b(again|already (wrote|emailed|called)|second time)\b/i
legal_or_chargeback_threat: /\b(lawyer|sue|legal|chargeback)\b/i
cancellation_risk: /\b(cancel|unsubscribe|switch(ing)? to)\b/i`;

// Each question describes what the writer does, so quoted or negated keywords do not count.
const DEFAULT_WORDING = {
  asks_refund_now: {
    instructions:
      "Does the customer ask, in this email, to get money back for a purchase (a refund, reversed charge or credit)? A refund that already happened, a question about the refund policy, or threatening a chargeback or bank dispute without asking the company for the money, is not asking now.",
  },
  wants_human: {
    instructions: "Does the customer ask to deal with a human person at the company instead of a bot or automated reply? Asking whether they are talking to a bot, or complaining about automated or template replies, counts.",
  },
  repeat_contact: {
    instructions: "Does the customer say they have already contacted support about this same issue before, by email, phone or chat?",
  },
  legal_or_chargeback_threat: {
    instructions: "Does the customer threaten legal action, a complaint to a regulator, or a chargeback / payment dispute with their bank? Asking the company itself to reverse a charge is not a threat.",
  },
  cancellation_risk: {
    instructions: "Does the customer say they will cancel, stop buying, or move to a competitor? Asking to cancel or unsubscribe counts, and so does a conditional threat to leave (\"one more mistake and…\"). A threat to go to the bank or a lawyer is not a cancellation. A cancellation that already happened does not count.",
  },
} satisfies Wording;

const DEFAULT_THRESHOLDS: Readonly<Record<Flag, BandThresholds>> = {
  asks_refund_now: { no: 0.2, yes: 0.8 },
  wants_human: { no: 0.2, yes: 0.8 },
  repeat_contact: { no: 0.2, yes: 0.8 },
  legal_or_chargeback_threat: { no: 0.2, yes: 0.8 },
  cancellation_risk: { no: 0.2, yes: 0.8 },
};

const none: FlagGold = {
  asks_refund_now: false,
  wants_human: false,
  repeat_contact: false,
  legal_or_chargeback_threat: false,
  cancellation_risk: false,
};

// Non-empty: each screen opens on its first preset.
const PRESETS: readonly [FlagsPreset, ...FlagsPreset[]] = [
  {
    id: "bot",
    label: "Are you a bot?",
    text: "Are you a bot? I've been going round in circles with this chat for twenty minutes.",
    gold: { ...none, wants_human: true },
    note: "Hints at wanting a person without asking for one: a case for the review band.",
  },
  {
    id: "not-a-lawyer",
    label: "Not a lawyer",
    text: "I'm not a lawyer, but charging me again after I cancelled seems wrong. Please reverse it.",
    gold: { ...none, asks_refund_now: true },
    note: "The regex fires on 'lawyer' and misses 'reverse it'.",
  },
  {
    id: "third-time",
    label: "Third time writing",
    text: "Third time writing about this and still nothing. Get me someone who can actually fix it.",
    gold: { ...none, wants_human: true, repeat_contact: true },
    note: "Repeat contact and a request for a person, with none of the keywords.",
  },
  {
    id: "manager",
    label: "My manager",
    text: "My manager asked me to order 40 more of these. Can you send a quote for next month?",
    gold: none,
    note: "'manager' is a colleague, not an escalation.",
  },
];

/** Each flag's first matching rule span, or null. Rules for unknown labels are ignored. */
export function flagsRegex(rules: readonly RegexRule[], text: string): Readonly<Record<Flag, Span | null>> {
  const out: Record<Flag, Span | null> = {
    asks_refund_now: null,
    wants_human: null,
    repeat_contact: null,
    legal_or_chargeback_threat: null,
    cancellation_risk: null,
  };
  for (const flag of FLAGS) {
    for (const rule of rules) {
      if (rule.label !== flag) continue;
      out[flag] = out[flag] ?? firstSpan(rule.pattern, text);
    }
  }
  return out;
}

export type FlagReading = { readonly flag: Flag; readonly p: number; readonly band: Band };

export function readFlags(response: JevResponse, thresholds: Readonly<Record<Flag, BandThresholds>>): readonly FlagReading[] {
  return FLAGS.map((flag) => {
    const p = noulOf(response, flag).noul;
    return { flag, p, band: band(p, thresholds[flag]) };
  });
}

export const flags = {
  id: "flags",
  defaultRules: DEFAULT_RULES,
  defaultWording: DEFAULT_WORDING,
  defaultThresholds: DEFAULT_THRESHOLDS,
  presets: PRESETS,
  presetInputs: PRESETS.map((p) => ({ text: p.text })),
  build({ raw, wording, model }) {
    const t = readText(raw);
    if (t.kind === "error") return t;
    const questions: Questions = Object.fromEntries(
      FLAGS.map((flag) => [flag, { type: "noul", instructions: wordingEntry(wording, DEFAULT_WORDING, flag).instructions }] as const),
    );
    return { kind: "ok", request: { model, state: t.text, questions } };
  },
} as const satisfies StationDef & Record<string, unknown>;
