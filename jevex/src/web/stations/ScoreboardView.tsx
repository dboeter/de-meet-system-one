import { useEffect, useState } from "react";
import { MODEL } from "../../core/config.ts";
import {
  againstNoise,
  corpusResponses,
  corpusTaskNoise,
  parseCorpus,
  PILOT,
  scoreCorpus,
  type NoiseComparison,
  type RepeatNoise,
  type StationRules,
  type Task,
} from "../../core/eval.ts";
import type { JevResponse } from "../../core/jev.ts";
import { parseRules } from "../../core/regex.ts";
import { flags } from "../../core/stations/flags.ts";
import { intent } from "../../core/stations/intent.ts";
import { triage } from "../../core/stations/triage.ts";
import corpusText from "../../../data/corpus.jsonl?raw";
import { RulesEditor, StationHeader } from "../components.tsx";
import { recordings } from "../recordings.ts";

const items = parseCorpus(corpusText);

const TASK_TITLES = {
  intent: "Intent",
  flags: "Flags (per flag)",
  "triage-department": "Triage: team",
  "triage-urgency": "Triage: urgency",
} as const;

type RuleKey = keyof StationRules;
const RULE_KEYS: readonly RuleKey[] = ["intent", "flags", "triage", "urgency"];
const DEFAULT_TEXTS: Readonly<Record<RuleKey, string>> = {
  intent: intent.defaultRules,
  flags: flags.defaultRules,
  triage: triage.defaultRules,
  urgency: triage.defaultUrgencyRule,
};
const RULE_LABELS: Readonly<Record<RuleKey, string>> = {
  intent: "Intent keyword ladder",
  flags: "Flag patterns",
  triage: "Routing table",
  urgency: "Urgency rule",
};


function gapText(c: NoiseComparison): string {
  if (c.kind === "no_pilot") return "–";
  const sign = c.gap > 0 ? "+" : "";
  return `${sign}${c.gap}`;
}

function noiseText(c: NoiseComparison): string {
  return c.kind === "no_pilot" ? "" : `noise ≤ ${c.noise}${c.beyondNoise ? "" : ", within it"}`;
}

function pct(n: number, d: number): string {
  return d === 0 ? "–" : `${Math.round((100 * n) / d)}%`;
}

function GapCell(props: { comparison: NoiseComparison }) {
  const noise = noiseText(props.comparison);
  return (
    <td className="num" data-testid="gap">
      {gapText(props.comparison)}
      {noise && <div className="muted small gap-noise">{noise}</div>}
    </td>
  );
}

export function ScoreboardView() {
  const [responses, setResponses] = useState<ReadonlyMap<string, JevResponse> | null>(null);
  const [noise, setNoise] = useState<Readonly<Record<Task, RepeatNoise>> | null>(null);
  const [texts, setTexts] = useState<Readonly<Record<RuleKey, string>>>(DEFAULT_TEXTS);
  const [editing, setEditing] = useState<RuleKey>("intent");

  useEffect(() => {
    void corpusResponses(items, recordings, MODEL).then(setResponses);
    void corpusTaskNoise(items, recordings, MODEL).then(setNoise);
  }, []);

  const parsed = {
    intent: parseRules(texts.intent),
    flags: parseRules(texts.flags),
    triage: parseRules(texts.triage),
    urgency: parseRules(texts.urgency),
  };
  const rules: StationRules | null =
    parsed.intent.kind === "ok" && parsed.flags.kind === "ok" && parsed.triage.kind === "ok" && parsed.urgency.kind === "ok"
      ? { intent: parsed.intent.rules, flags: parsed.flags.rules, triage: parsed.triage.rules, urgency: parsed.urgency.rules }
      : null;
  const score = rules && responses ? scoreCorpus({ items, rules, responses }) : null;
  const edited = RULE_KEYS.some((k) => texts[k] !== DEFAULT_TEXTS[k]);

  return (
    <>
      <StationHeader
        title="Scoreboard"
        code="regex vs Jev"
        blurb={`Both, over every labelled email (${items.length} cases). Jev's answers are recorded, so pasting a better regex rescores it instantly, without asking Jev anything.`}
      />
      <div className="scoreboard">
        <section className="card">
          <h2>Accuracy</h2>
          {!score ? (
            <p className="muted">{rules ? "Loading recorded answers…" : "Fix the regex to score it."}</p>
          ) : (
            <table className="score-table" data-testid="score-table">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Decisions</th>
                  <th className="col-regex-h">Regex{edited ? " (yours)" : ""}</th>
                  <th className="col-jev-h">Jev</th>
                  <th title="Jev's right decisions minus regex's, against how many decisions repeat noise could move">Gap</th>
                </tr>
              </thead>
              <tbody>
                {score.tasks.map((t) => (
                  <tr key={t.task} data-testid={`score-${t.task}`}>
                    <td>{TASK_TITLES[t.task]}</td>
                    <td>{t.total === 0 ? "no labelled cases yet" : t.total}</td>
                    <td className="num">{pct(t.regexCorrect, t.total)}</td>
                    <td className="num">
                      {pct(t.jevCorrect, t.total)}
                      {t.jevMissing > 0 && <span className="muted small"> ({t.jevMissing} not recorded)</span>}
                      {t.jevReview > 0 && <span className="muted small"> ({t.jevReview} to review)</span>}
                    </td>
                    <GapCell comparison={againstNoise(t, noise?.[t.task] ?? { items: 0, flipped: 0, maxDelta: 0 })} />
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="muted small">
            {MODEL}. Cases tagged ambiguous are left out of accuracy ({score?.tasks.reduce((n, t) => n + t.excluded, 0) ?? 0}).
            {score && noise && (
              <>
                {" "}
                Repeat noise, cases asked {PILOT.repeats} times that changed the decision:{" "}
                {score.tasks
                  .filter((t) => noise[t.task].items > 0)
                  .map((t) => `${TASK_TITLES[t.task]} ${noise[t.task].flipped} of ${noise[t.task].items}`)
                  .join(", ")}
                . Noise ≤ N is the 95% upper bound on decisions it could move.
              </>
            )}
          </p>
        </section>
        <section className="card">
          <h2>Paste your regex</h2>
          <div className="chips">
            {RULE_KEYS.map((k) => (
              <button key={k} type="button" className={k === editing ? "chip selected" : "chip"} onClick={() => setEditing(k)}>
                {RULE_LABELS[k]}
              </button>
            ))}
          </div>
          <RulesEditor value={texts[editing]} onChange={(v) => setTexts({ ...texts, [editing]: v })} label={RULE_LABELS[editing]} />
        </section>
      </div>
      {score && (
        <section className="card disagreements">
          <h2>Where regex and Jev disagree ({score.disagreements.length})</h2>
          <table className="score-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Decision</th>
                <th>Expected</th>
                <th className="col-regex-h">Regex</th>
                <th className="col-jev-h">Jev</th>
              </tr>
            </thead>
            <tbody>
              {score.disagreements.map((d) => (
                <tr key={`${d.id}-${d.task}`}>
                  <td className="email-cell">{d.text}</td>
                  <td>
                    <code>{d.task}</code>
                  </td>
                  <td>
                    <code>{d.gold}</code>
                  </td>
                  <td className={d.regex === d.gold ? "cell-ok" : "cell-bad"}>
                    <code>{d.regex}</code>
                  </td>
                  <td className={d.jev === d.gold ? "cell-ok" : "cell-bad"}>
                    <code>{d.jev}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}
