import { choiceOf, ranked, scoreOf, type JevResponse } from "../jev.ts";
import { firstMatch, type RegexRule, type Span } from "../regex.ts";
import { wordingEntry, type Wording, type WordingEntry } from "../wording.ts";
import { readText, type StationDef } from "./station.ts";

export const DEPARTMENTS = ["returns", "shipping", "billing", "account", "other"] as const;
export type Department = (typeof DEPARTMENTS)[number];
export type TriageGold = { readonly department: Department; readonly urgent: boolean };

export type TriagePreset = { readonly id: string; readonly label: string; readonly text: string; readonly gold: TriageGold; readonly note: string };

const DEFAULT_RULES = String.raw`shipping: /\b(deliver\w*|shipping|package|parcel|tracking|arrived)\b/i
returns: /\b(return|exchange|wrong size|doesn't fit)\b/i
billing: /\b(charge\w*|invoice|payment|refund|billing)\b/i
account: /\b(password|log ?in|account)\b/i`;

const DEFAULT_URGENCY_RULE = String.raw`urgent: /!{2,}|\b(urgent|asap|today|immediately)\b/i`;

const DEFAULT_WORDING = {
  department: {
    instructions: "Which team should handle this email?",
    criteria: {
      returns: "Sending items back or swapping them, wrong or damaged items; not the refund itself",
      shipping: "Delivery status, delays, lost or misdelivered packages",
      billing: "Charges, invoices, refunds of payments (including money for items already sent back), payment problems",
      account: "Logging in, passwords, account settings",
      other: "Anything else, including feedback that needs no team",
    },
  },
  // Score levels, keyed by position; the request sends them as an ordered list.
  urgency: {
    instructions: "How soon does this email need a response?",
    criteria: {
      "0": "Can wait: no deadline, no harm from waiting a week",
      "1": "Within a few days: a real problem, but nothing is lost by waiting a day or two",
      "2": "Today: a deadline or event within the next day or two, or harm that gets worse with every hour of waiting (money still being taken, a business that cannot operate)",
    },
  },
  return_reason: {
    instructions: "If the customer wants to return or exchange something, why?",
    criteria: {
      wrong_size: "The item doesn't fit",
      wrong_item: "A different product was delivered",
      damaged: "The item arrived broken or stopped working",
      changed_mind: "The item is fine, the customer no longer wants it",
      other: "Another reason, or no return is asked for",
    },
  },
  shipping_issue: {
    instructions: "If this is a delivery problem, which kind?",
    criteria: {
      not_delivered: "The package never arrived",
      delayed: "The package is late or stuck but still on its way",
      wrong_address: "The package went to the wrong place",
      damaged_in_transit: "The package arrived damaged",
      other: "Another delivery problem, or none",
    },
  },
} satisfies Wording;

const BRANCH: Partial<Record<Department, "return_reason" | "shipping_issue">> = {
  returns: "return_reason",
  shipping: "shipping_issue",
};

// Non-empty: each screen opens on its first preset.
const PRESETS: readonly [TriagePreset, ...TriagePreset[]] = [
  {
    id: "charged-twice",
    label: "Charged twice",
    text: "I was charged twice for a package that never came.",
    gold: { department: "billing", urgent: false },
    note: "A billing problem that mentions a delivery; shipping may get a copy.",
  },
  {
    id: "wedding",
    label: "Wedding on Saturday",
    text: "Hi! The dress for my sister's wedding on Saturday still says 'label created'. Could you check where it is?",
    gold: { department: "shipping", urgent: true },
    note: "Calm and polite, but there is a deadline.",
  },
  {
    id: "shouting",
    label: "Shouting",
    text: "THIS IS RIDICULOUS!!! The new logo is hideous and I want everyone to know it!!!",
    gold: { department: "other", urgent: false },
    note: "Angry, but nothing needs doing soon.",
  },
  {
    id: "swap",
    label: "Swap for a large",
    text: "The jacket is lovely but a size too small. Can I swap it for a large?",
    gold: { department: "returns", urgent: false },
    note: "An exchange with none of the routing keywords.",
  },
];

export type TriageThresholds = {
  /** Below this department confidence, a person triages. */
  readonly minConfidence: number;
  /** A runner-up team above this probability gets a copy. */
  readonly copyAbove: number;
  /** Urgency score (0–2) at or above which the email is urgent. */
  readonly urgentAt: number;
};

const DEFAULT_THRESHOLDS: TriageThresholds = { minConfidence: 0.5, copyAbove: 0.25, urgentAt: 1.5 };

export type TriagePath =
  | { readonly kind: "manual"; readonly best: Department }
  | {
      readonly kind: "auto";
      readonly team: Department;
      readonly copies: readonly Department[];
      readonly issue: { readonly question: "return_reason" | "shipping_issue"; readonly label: string; readonly p: number } | null;
    };

export type TriageReading = {
  readonly path: TriagePath;
  readonly departments: readonly { readonly label: string; readonly p: number }[];
  readonly confidence: number;
  readonly urgency: number;
  readonly urgent: boolean;
};

function isDepartment(v: string): v is Department {
  return (DEPARTMENTS as readonly string[]).includes(v);
}

/** The code path a support system would take for these answers. Unused branches are ignored. */
export function route(response: JevResponse, t: TriageThresholds): TriageReading {
  const dept = choiceOf(response, "department");
  const urgency = scoreOf(response, "urgency").score;
  const departments = ranked(dept);
  // The criteria keys are DEPARTMENTS, so any other answer is a protocol surprise; route it as `other`.
  const best: Department = isDepartment(dept.choice) ? dept.choice : "other";
  let path: TriagePath;
  if (dept.confidence < t.minConfidence) {
    path = { kind: "manual", best };
  } else {
    const branch = BRANCH[best];
    const issue = branch ? choiceOf(response, branch) : null;
    path = {
      kind: "auto",
      team: best,
      copies: departments.flatMap((d) => (d.label !== best && d.p > t.copyAbove && isDepartment(d.label) ? [d.label] : [])),
      issue: branch && issue ? { question: branch, label: issue.choice, p: issue.probabilities[issue.choice] ?? 0 } : null,
    };
  }
  return { path, departments, confidence: dept.confidence, urgency, urgent: urgency >= t.urgentAt };
}

export type TriageRegexVerdict = {
  /** A department, or `none` when no row matched (a rule label the viewer typed may be anything). */
  readonly department: string;
  readonly departmentSpan: Span | null;
  readonly urgent: boolean;
  readonly urgentSpan: Span | null;
};

export function triageRegex(args: {
  readonly routing: readonly RegexRule[];
  readonly urgency: readonly RegexRule[];
  readonly text: string;
}): TriageRegexVerdict {
  const dept = firstMatch(args.routing, args.text);
  const urgent = firstMatch(args.urgency, args.text);
  return {
    department: dept?.label ?? "none",
    departmentSpan: dept?.span ?? null,
    urgent: urgent !== null,
    urgentSpan: urgent?.span ?? null,
  };
}

const URGENCY_LEVELS = ["0", "1", "2"] as const;

/** Score levels in order; a cleared or missing level falls back to its default description. */
function scoreLevels(entry: WordingEntry): [string, string, ...string[]] {
  const level = (k: (typeof URGENCY_LEVELS)[number]) => entry.criteria?.[k] ?? DEFAULT_WORDING.urgency.criteria[k];
  return [level("0"), level("1"), level("2")];
}

export const triage = {
  id: "triage",
  defaultRules: DEFAULT_RULES,
  defaultUrgencyRule: DEFAULT_URGENCY_RULE,
  defaultWording: DEFAULT_WORDING,
  defaultThresholds: DEFAULT_THRESHOLDS,
  presets: PRESETS,
  presetInputs: PRESETS.map((p) => ({ text: p.text })),
  build({ raw, wording, model }) {
    const t = readText(raw);
    if (t.kind === "error") return t;
    const choice = (key: "department" | "return_reason" | "shipping_issue") => {
      const w = wordingEntry(wording, DEFAULT_WORDING, key);
      return { type: "choice", instructions: w.instructions, criteria: w.criteria ?? {} } as const;
    };
    const u = wordingEntry(wording, DEFAULT_WORDING, "urgency");
    return {
      kind: "ok",
      request: {
        model,
        state: t.text,
        questions: {
          department: choice("department"),
          urgency: { type: "score", instructions: u.instructions, criteria: scoreLevels(u) },
          return_reason: choice("return_reason"),
          shipping_issue: choice("shipping_issue"),
        },
      },
    };
  },
} as const satisfies StationDef & Record<string, unknown>;
