import { choiceOf, type JevResponse } from "../jev.ts";
import { findAll, parseRules, type Span } from "../regex.ts";
import { wordingEntry, type Wording } from "../wording.ts";
import { isRecord } from "../guards.ts";
import { readText, type BuildResult, type StationDef } from "./station.ts";

export const KINDS = ["order", "amount", "email"] as const;
export type Kind = (typeof KINDS)[number];

/** The escape hatch on every pick: none of the candidates is the requested value. */
export const NONE = "none";
/** A Choice allows at most 255 options; one is `none`. */
export const MAX_CANDIDATES = 254;

export type ExtractPreset = {
  readonly id: string;
  readonly label: string;
  readonly kind: Kind;
  readonly text: string;
  readonly gold: string;
  readonly note: string;
};

/** Finder patterns as editable rule text: one `kind: /pattern/flags` line each. */
const FINDERS: Readonly<Record<Kind, string>> = {
  order: String.raw`order: /\bA-\d{3,}\b/`,
  amount: String.raw`amount: /-?[$€£]\s?\d[\d,]*(?:\.\d{2})?/`,
  email: String.raw`email: /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/`,
};

const DEFAULT_WORDING = {
  order: { instructions: "Which order does the customer want refunded?" },
  amount: { instructions: "Which amount was the customer actually charged in total?" },
  email: { instructions: "Which email address does the customer want the receipt sent to?" },
} satisfies Wording;

// Non-empty: each screen opens on its first preset.
const PRESETS: readonly [ExtractPreset, ...ExtractPreset[]] = [
  {
    id: "order",
    label: "Which order?",
    kind: "order",
    text: "Orders A-1182 and A-1190 arrived. A-1182 is fine, but the lamp in A-1190 is cracked and I want my money back for it.",
    gold: "A-1190",
    note: "Both order numbers match; only one is the problem.",
  },
  {
    id: "amount",
    label: "Amount charged",
    kind: "amount",
    text: "Invoice #8812\nSubtotal: $1,240.00\nShipping: $45.00\nDiscount: -$100.00\nTax: $130.50\nTotal charged: $1,315.50\nPrevious balance: $0.00",
    gold: "$1,315.50",
    note: "Six amounts; the first is the subtotal.",
  },
  {
    id: "email",
    label: "Receipt address",
    kind: "email",
    text: "Can you resend the receipt? Not to jdv1987@gmail.example, that inbox is full, but to my work address jan.devries@acme-logistics.example. You can reply to support@shop.example as usual.",
    gold: "jan.devries@acme-logistics.example",
    note: "Three addresses; the first is the one to avoid.",
  },
];

export type Found = { readonly spans: readonly Span[]; readonly candidates: readonly string[] };

/** All matches of a finder (rule text), and the distinct values in order of first appearance. */
export function findCandidates(finder: string, text: string): Found {
  const parsed = parseRules(finder);
  if (parsed.kind === "error") return { spans: [], candidates: [] };
  const spans = parsed.rules.flatMap((r) => findAll(r.pattern, text)).sort((a, b) => a.start - b.start);
  return { spans, candidates: [...new Set(spans.map((s) => s.text))] };
}

export type Pick = { readonly kind: "picked"; readonly value: string; readonly p: number } | { readonly kind: "none"; readonly p: number };

export class NotACandidateError extends Error {
  override name = "NotACandidateError";
}

/** Jev's pick. It can only be one of the candidates or `none`; anything else is refused. */
export function readPick(response: JevResponse, candidates: readonly string[]): Pick {
  const answer = choiceOf(response, "pick");
  const p = answer.probabilities[answer.choice] ?? 0;
  if (answer.choice === NONE) return { kind: "none", p };
  if (!candidates.includes(answer.choice)) throw new NotACandidateError(`"${answer.choice}" is not one of the candidates`);
  return { kind: "picked", value: answer.choice, p };
}

function isKind(v: unknown): v is Kind {
  return typeof v === "string" && (KINDS as readonly string[]).includes(v);
}

function build(args: { raw: unknown; wording: Wording; model: string }): BuildResult {
  const t = readText(args.raw);
  if (t.kind === "error") return t;
  if (!isRecord(args.raw) || !isKind(args.raw.kind)) return { kind: "error", reason: "invalid", message: `input.kind must be one of ${KINDS.join(", ")}` };
  const candidates = args.raw.candidates;
  if (!Array.isArray(candidates) || candidates.length === 0 || candidates.length > MAX_CANDIDATES) {
    return { kind: "error", reason: "invalid", message: `input.candidates must list 1–${MAX_CANDIDATES} values` };
  }
  const unique = new Set<string>();
  for (const c of candidates) {
    // Every option must be a verbatim span of the text, so the answer is always copied, never written.
    if (typeof c !== "string" || c === "" || c === NONE || !t.text.includes(c) || unique.has(c)) {
      return { kind: "error", reason: "invalid", message: "every candidate must be a distinct span of the text" };
    }
    unique.add(c);
  }
  const criteria: Record<string, string | null> = Object.fromEntries([...unique].map((c) => [c, null]));
  criteria[NONE] = "None of these is the requested value.";
  return {
    kind: "ok",
    request: {
      model: args.model,
      state: t.text,
      questions: { pick: { type: "choice", instructions: wordingEntry(args.wording, DEFAULT_WORDING, args.raw.kind).instructions, criteria } },
    },
  };
}

export const extract = {
  id: "extract",
  finders: FINDERS,
  defaultWording: DEFAULT_WORDING,
  presets: PRESETS,
  presetInputs: PRESETS.map((p) => ({ kind: p.kind, text: p.text, candidates: findCandidates(FINDERS[p.kind], p.text).candidates })),
  build,
} as const satisfies StationDef & Record<string, unknown>;
