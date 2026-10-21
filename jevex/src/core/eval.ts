/**
 * Score the regex baselines and recorded Jev answers over the labelled corpus. The eval script
 * and the Scoreboard both call this, so they show the same numbers by construction.
 */
import { isRecord } from "./guards.ts";
import { choiceOf, noulOf, scoreOf, type JevRequest, type JevResponse } from "./jev.ts";
import { recordingKey, type RecordingStore } from "./recording.ts";
import type { RegexRule } from "./regex.ts";
import { FLAGS, flags, flagsRegex, type FlagGold } from "./stations/flags.ts";
import { band } from "./thresholds.ts";
import { INTENTS, intent, intentRegexVerdict, type Intent } from "./stations/intent.ts";
import { DEPARTMENTS, triage, triageRegex, type TriageGold } from "./stations/triage.ts";
import type { RecordingTarget } from "./targets.ts";

type Base = { readonly id: string; readonly text: string; readonly tags: readonly string[]; readonly note: string };
export type CorpusItem =
  | (Base & { readonly station: "intent"; readonly gold: Intent })
  | (Base & { readonly station: "flags"; readonly gold: FlagGold })
  | (Base & { readonly station: "triage"; readonly gold: TriageGold });

function parseItem(v: unknown): CorpusItem | null {
  if (!isRecord(v) || typeof v.id !== "string" || typeof v.text !== "string") return null;
  const tags = Array.isArray(v.tags) && v.tags.every((t) => typeof t === "string") ? (v.tags as string[]) : null;
  if (!tags) return null;
  const base = { id: v.id, text: v.text, tags, note: typeof v.note === "string" ? v.note : "" };
  const gold = v.gold;
  switch (v.station) {
    case "intent": {
      const label = INTENTS.find((i) => i === gold);
      return label ? { ...base, station: "intent", gold: label } : null;
    }
    case "flags": {
      if (!isRecord(gold) || !FLAGS.every((f) => typeof gold[f] === "boolean")) return null;
      const g = Object.fromEntries(FLAGS.map((f) => [f, gold[f] === true])) as Record<(typeof FLAGS)[number], boolean>;
      return { ...base, station: "flags", gold: g };
    }
    case "triage": {
      if (!isRecord(gold) || typeof gold.urgent !== "boolean") return null;
      const department = DEPARTMENTS.find((d) => d === gold.department);
      return department ? { ...base, station: "triage", gold: { department, urgent: gold.urgent } } : null;
    }
    default:
      return null;
  }
}

export function parseCorpus(jsonl: string): CorpusItem[] {
  const out: CorpusItem[] = [];
  for (const [i, line] of jsonl.split("\n").entries()) {
    if (line.trim() === "") continue;
    let item: CorpusItem | null = null;
    try {
      item = parseItem(JSON.parse(line));
    } catch {
      item = null;
    }
    if (!item) throw new Error(`Malformed corpus item on line ${i + 1}`);
    out.push(item);
  }
  return out;
}

/** The Jev request for a corpus item, with the station's frozen default wording. */
export function corpusRequest(item: CorpusItem, model: string): JevRequest {
  const station = { intent, flags, triage }[item.station];
  const built = station.build({ raw: { text: item.text }, wording: station.defaultWording, model });
  if (built.kind === "error") throw new Error(`Corpus item ${item.id} does not build: ${built.message}`);
  return built.request;
}

/**
 * Repeats recorded to measure repeat noise: the first `items` cases of a station, or all of
 * them. Flags and triage repeat every case, because a 10-case pilot left their gaps within
 * its wide upper bound.
 */
export const PILOT: { readonly repeats: number; readonly items: Readonly<Record<CorpusItem["station"], number | "all">> } = {
  repeats: 3,
  items: { intent: 10, flags: "all", triage: "all" },
};

export function corpusTargets(items: readonly CorpusItem[], model: string): RecordingTarget[] {
  const seen: Record<string, number> = {};
  return items.map((item) => {
    const n = (seen[item.station] = (seen[item.station] ?? 0) + 1);
    const pilot = PILOT.items[item.station];
    return { label: `corpus ${item.id}`, request: corpusRequest(item, model), repeats: pilot === "all" || n <= pilot ? PILOT.repeats : 1 };
  });
}

/** Recorded answers for each corpus item (repeat 0), keyed by item id. */
export async function corpusResponses(items: readonly CorpusItem[], store: RecordingStore, model: string): Promise<Map<string, JevResponse>> {
  const out = new Map<string, JevResponse>();
  for (const item of items) {
    const rec = store.get(await recordingKey(corpusRequest(item, model)));
    if (rec) out.set(item.id, rec.response);
  }
  return out;
}

export type Task = "intent" | "flags" | "triage-department" | "triage-urgency";

export type TaskScore = {
  readonly task: Task;
  /** Scored decisions (ambiguous cases excluded). */
  readonly total: number;
  /** Cases tagged `ambiguous`, left out of accuracy (rubric rule 9). */
  readonly excluded: number;
  readonly regexCorrect: number;
  readonly jevCorrect: number;
  /** Decisions with no recorded Jev answer; they count as wrong. */
  readonly jevMissing: number;
  /** Flag decisions Jev left in the review band, as the Flags screen does; neither right nor wrong. */
  readonly jevReview: number;
};

export type Disagreement = {
  readonly id: string;
  readonly task: string;
  readonly text: string;
  readonly gold: string;
  readonly regex: string;
  readonly jev: string;
};

export type Score = { readonly tasks: readonly TaskScore[]; readonly disagreements: readonly Disagreement[] };

export type StationRules = {
  readonly intent: readonly RegexRule[];
  readonly flags: readonly RegexRule[];
  readonly triage: readonly RegexRule[];
  readonly urgency: readonly RegexRule[];
};

type Decision = { task: Task; label: string; gold: string; regex: string; jev: string | null };

const yesNo = (b: boolean) => (b ? "yes" : "no");
const urgentLabel = (b: boolean) => (b ? "urgent" : "not urgent");

function decisions(item: CorpusItem, rules: StationRules, response: JevResponse | undefined): Decision[] {
  switch (item.station) {
    case "intent": {
      // The rubric scores a regex `none` as `other`.
      const regex = intentRegexVerdict(rules.intent, item.text).label;
      return [{ task: "intent", label: "intent", gold: item.gold, regex: regex === "none" ? "other" : regex, jev: response ? choiceOf(response, "intent").choice : null }];
    }
    case "flags": {
      const hits = flagsRegex(rules.flags, item.text);
      // The same yes / review / no bands the Flags screen draws at its default thresholds.
      return FLAGS.map((f) => ({
        task: "flags",
        label: `flags:${f}`,
        gold: yesNo(item.gold[f]),
        regex: yesNo(hits[f] !== null),
        jev: response ? band(noulOf(response, f).noul, flags.defaultThresholds[f]) : null,
      }));
    }
    case "triage": {
      const r = triageRegex({ routing: rules.triage, urgency: rules.urgency, text: item.text });
      return [
        {
          task: "triage-department",
          label: "triage-department",
          gold: item.gold.department,
          regex: r.department === "none" ? "other" : r.department,
          jev: response ? choiceOf(response, "department").choice : null,
        },
        {
          task: "triage-urgency",
          label: "triage-urgency",
          gold: urgentLabel(item.gold.urgent),
          regex: urgentLabel(r.urgent),
          jev: response ? urgentLabel(scoreOf(response, "urgency").score >= triage.defaultThresholds.urgentAt) : null,
        },
      ];
    }
    default: {
      const _exhaustive: never = item;
      return _exhaustive;
    }
  }
}

const TASKS: readonly Task[] = ["intent", "flags", "triage-department", "triage-urgency"];

export function scoreCorpus(args: {
  readonly items: readonly CorpusItem[];
  readonly rules: StationRules;
  readonly responses: ReadonlyMap<string, JevResponse>;
}): Score {
  const empty = () => ({ total: 0, excluded: 0, regexCorrect: 0, jevCorrect: 0, jevMissing: 0, jevReview: 0 });
  const tally = new Map<Task, ReturnType<typeof empty>>(TASKS.map((t) => [t, empty()]));
  const disagreements: Disagreement[] = [];
  for (const item of args.items) {
    const ambiguous = item.tags.includes("ambiguous");
    for (const d of decisions(item, args.rules, args.responses.get(item.id))) {
      const t = tally.get(d.task);
      if (!t) continue;
      if (ambiguous) {
        t.excluded++;
        continue;
      }
      t.total++;
      if (d.regex === d.gold) t.regexCorrect++;
      if (d.jev === null) t.jevMissing++;
      else if (d.jev === "review") t.jevReview++;
      else if (d.jev === d.gold) t.jevCorrect++;
      if (d.jev !== null && d.jev !== d.regex) {
        disagreements.push({ id: item.id, task: d.label, text: item.text, gold: d.gold, regex: d.regex, jev: d.jev });
      }
    }
  }
  return { tasks: TASKS.map((task) => ({ task, ...(tally.get(task) ?? empty()) })), disagreements };
}

/** What repeat noise is measured on for one task: the questions it scores and the decision it reads from them. */
export type NoiseSpec = { readonly questions: readonly string[]; readonly decide: (response: JevResponse) => string };

/**
 * Per task, only the scored decision counts as a flip: an unused branch question (say
 * `shipping_issue` on a billing email) changing between repeats does not move the score.
 */
export const TASK_NOISE: Readonly<Record<Task, NoiseSpec>> = {
  intent: { questions: ["intent"], decide: (r) => choiceOf(r, "intent").choice },
  flags: { questions: FLAGS, decide: (r) => FLAGS.map((f) => band(noulOf(r, f).noul, flags.defaultThresholds[f])).join(",") },
  "triage-department": { questions: ["department"], decide: (r) => choiceOf(r, "department").choice },
  "triage-urgency": { questions: ["urgency"], decide: (r) => urgentLabel(scoreOf(r, "urgency").score >= triage.defaultThresholds.urgentAt) },
};

function probabilities(response: JevResponse, questions: readonly string[]): Map<string, number> {
  const out = new Map<string, number>();
  for (const id of questions) {
    const a = response.answers[id];
    if (!a) continue;
    if (a.type === "noul") out.set(id, a.noul);
    else for (const [k, p] of Object.entries(a.probabilities)) out.set(`${id}.${k}`, p);
  }
  return out;
}

export type RepeatNoise = { readonly items: number; readonly flipped: number; readonly maxDelta: number };

/** Across groups of identical calls: how many changed the task's decision, and the largest probability move in its questions. */
export function repeatNoise(groups: readonly (readonly JevResponse[])[], spec: NoiseSpec): RepeatNoise {
  let items = 0;
  let flipped = 0;
  let maxDelta = 0;
  for (const group of groups) {
    if (group.length < 2) continue;
    items++;
    if (new Set(group.map(spec.decide)).size > 1) flipped++;
    const maps = group.map((r) => probabilities(r, spec.questions));
    const keys = new Set(maps.flatMap((m) => [...m.keys()]));
    for (const k of keys) {
      const ps = maps.map((m) => m.get(k) ?? 0);
      maxDelta = Math.max(maxDelta, Math.max(...ps) - Math.min(...ps));
    }
  }
  return { items, flipped, maxDelta };
}

/** Repeat groups for one station's corpus items that have more than one recording. */
export async function corpusRepeatGroups(
  items: readonly CorpusItem[],
  station: CorpusItem["station"],
  store: RecordingStore,
  model: string,
): Promise<JevResponse[][]> {
  const groups: JevResponse[][] = [];
  for (const item of items) {
    if (item.station !== station) continue;
    const recs = store.repeats(await recordingKey(corpusRequest(item, model)));
    if (recs.length > 1) groups.push(recs.map((r) => r.response));
  }
  return groups;
}

export const TASK_STATION: Readonly<Record<Task, CorpusItem["station"]>> = {
  intent: "intent",
  flags: "flags",
  "triage-department": "triage",
  "triage-urgency": "triage",
};

/** 95% Wilson upper bound on a rate seen as `hits` out of `n`. */
function upperRate(hits: number, n: number): number {
  const z = 1.96;
  const p = hits / n;
  const z2n = (z * z) / n;
  return (p + z2n / 2 + z * Math.sqrt(p * (1 - p) / n + z2n / (4 * n))) / (1 + z2n);
}

export type NoiseComparison =
  | { readonly kind: "no_pilot" }
  | {
      readonly kind: "compared";
      /** Jev's right decisions minus regex's. */
      readonly gap: number;
      /**
       * How many of this task's decisions repeat noise could change, at the 95% upper bound of
       * the pilot's flip rate. A case that flips may flip all its decisions, so the bound is
       * rate × decisions.
       */
      readonly noise: number;
      readonly beyondNoise: boolean;
    };

/** Report a task's regex-vs-Jev gap against the repeat noise measured on its station's pilot. */
export function againstNoise(task: TaskScore, noise: RepeatNoise): NoiseComparison {
  if (noise.items === 0 || task.total === 0) return { kind: "no_pilot" };
  const gap = task.jevCorrect - task.regexCorrect;
  const bound = Math.ceil(upperRate(noise.flipped, noise.items) * task.total);
  return { kind: "compared", gap, noise: bound, beyondNoise: Math.abs(gap) > bound };
}

/** Repeat noise for every task, each measured on its own station's repeated cases and its own decision. */
export async function corpusTaskNoise(items: readonly CorpusItem[], store: RecordingStore, model: string): Promise<Record<Task, RepeatNoise>> {
  const groups = {
    intent: await corpusRepeatGroups(items, "intent", store, model),
    flags: await corpusRepeatGroups(items, "flags", store, model),
    triage: await corpusRepeatGroups(items, "triage", store, model),
  };
  const noise = (task: Task) => repeatNoise(groups[TASK_STATION[task]], TASK_NOISE[task]);
  return {
    intent: noise("intent"),
    flags: noise("flags"),
    "triage-department": noise("triage-department"),
    "triage-urgency": noise("triage-urgency"),
  };
}
