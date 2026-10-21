import type { ViewStart } from "./start.ts";
import type { ViewId } from "./views.ts";

export type GuidedStep = {
  readonly view: ViewId;
  readonly title: string;
  /** What the screen opens on; defaults to its first preset. */
  readonly start?: ViewStart;
  /** CSS selector to draw attention to. */
  readonly highlight?: string;
  readonly note: string;
};

/** The five-minute story. Every step replays recorded answers, so it runs offline. */
export const GUIDED: readonly [GuidedStep, ...GuidedStep[]] = [
  {
    view: "intent",
    title: "The refund that already happened",
    start: { kind: "preset", presetId: "came-through" },
    highlight: ".col-regex .answer",
    note: "A keyword ladder sees 'refund' and routes it as a refund request. Jev reads that the refund already came through and the customer is saying thanks.",
  },
  {
    view: "intent",
    title: "Negation",
    start: { kind: "preset", presetId: "negation" },
    highlight: ".col-jev .answer",
    note: "'I don't want a refund': the keyword is there, the intent is the opposite. Every fix you add to the ladder breaks another email. Jev answers exchange, with a probability for every option.",
  },
  {
    view: "flags",
    title: "Several things at once, and an honest 'not sure'",
    start: { kind: "preset", presetId: "bot" },
    highlight: ".col-jev",
    note: "Five yes/no questions in one request. 'Are you a bot?' hints at wanting a person without asking: Jev puts it in the middle, so it goes to review. Move a slider: nothing is asked again.",
  },
  {
    view: "triage",
    title: "Route with confidence",
    start: { kind: "preset", presetId: "charged-twice" },
    highlight: "[data-testid=triage-path]",
    note: "The routing table sees 'package' and sends a double charge to shipping. Jev picks billing. Confidence decides whether code routes it or a person looks first; a runner-up team can get a copy.",
  },
  {
    view: "extract",
    title: "Keep your regex",
    start: { kind: "preset", presetId: "order" },
    highlight: ".col-jev",
    note: "Regex and Jev together. The regex finds both order numbers; Jev picks the one the customer wants refunded. The answer is always one of the highlighted spans, copied unchanged: it can be wrong, never invented.",
  },
  {
    view: "scoreboard",
    title: "Not just hand-picked examples",
    highlight: "[data-testid=score-table]",
    note: "Over every labelled email, not only the presets. Paste a better regex and it rescores instantly; Jev's answers are already recorded. The disagreements list is where an existing regex gets audited.",
  },
  {
    view: "keep",
    title: "When to keep the regex",
    note: "Regex and code still own format, exact IDs and arithmetic. Jev owns meaning. The strongest pattern combines them.",
  },
  {
    view: "intent",
    title: "Your turn",
    start: { kind: "blank" },
    highlight: "[data-testid=email-input]",
    note: "Ask the room for an email. Switch to Live with the pill (top right) and press Ask.",
  },
];
