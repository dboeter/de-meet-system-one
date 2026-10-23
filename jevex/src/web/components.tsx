import { useId, useRef, useState, type ReactNode } from "react";
import { sdkSnippet } from "../core/code.ts";
import { costUsd } from "../core/config.ts";
import { parseRules, type Span } from "../core/regex.ts";
import type { WordingEntry } from "../core/wording.ts";
import { useDemo } from "./demo.tsx";
import type { Jev, JevResult } from "./useJev.ts";

export function StationHeader(props: { title: string; code: string; blurb: ReactNode }) {
  return (
    <header className="station-header">
      <h1>
        {props.title} <code>{props.code}</code>
      </h1>
      <p>{props.blurb}</p>
    </header>
  );
}

export function PresetChips<P extends { id: string; label: string }>(props: {
  presets: readonly P[];
  selected: string | null;
  onPick: (preset: P) => void;
}) {
  const { presenting } = useDemo();
  if (presenting) return null;
  return (
    <div className="chips" role="group" aria-label="Examples">
      {props.presets.map((p) => (
        <button
          key={p.id}
          type="button"
          className={p.id === props.selected ? "chip selected" : "chip"}
          aria-pressed={p.id === props.selected}
          onClick={() => props.onPick(p)}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

/** The email across the top with its note beside it; Jev's answer below, the regex's next to it. */
export function Columns(props: { input: ReactNode; note?: ReactNode; regex: ReactNode; jev: ReactNode; below?: ReactNode }) {
  return (
    <>
    <div className="columns">
      <section className="card col-input" aria-label="Input">
        <div className="input-main">{props.input}</div>
        {props.note && <div className="input-note">{props.note}</div>}
      </section>
      <section className="card col-jev" aria-label="Jev">
        <h2>Jev</h2>
        {props.jev}
      </section>
      <section className="card col-regex" aria-label="Regex">
        <h2>Regex</h2>
        {props.regex}
      </section>
    </div>
    {props.below}
    </>
  );
}

type Mark = Span & { className?: string; title?: string };

/**
 * The email, editable, with the regex's matches (and Jev's pick) marked on the text itself,
 * so the screen shows the email once. The marks sit on a backdrop behind a transparent
 * textarea; both use the same font, padding and wrapping, which is what keeps them aligned.
 */
export function EmailInput(props: {
  value: string;
  onChange: (v: string) => void;
  onAsk: () => void;
  label?: string;
  rows?: number;
  marks?: readonly Mark[];
}) {
  const id = useId();
  const { presenting } = useDemo();
  const [edited, setEdited] = useState(false);
  const backdrop = useRef<HTMLDivElement>(null);
  // Presenting hides Ask until the presenter types, or on the blank live box.
  const showAsk = !presenting || edited || props.value === "";
  return (
    <div className="field">
      <label htmlFor={id}>{props.label ?? "Email"}</label>
      <div className="email-box">
        <div className="email-backdrop" ref={backdrop} aria-hidden>
          <Marked text={props.value} spans={props.marks ?? []} />
          {/* A trailing newline in a textarea adds a line; the backdrop needs one too. */}
          {"\n"}
        </div>
        <textarea
          id={id}
          data-testid="email-input"
          value={props.value}
          rows={props.rows ?? 4}
          onScroll={(e) => {
            if (backdrop.current) backdrop.current.scrollTop = e.currentTarget.scrollTop;
          }}
          onChange={(e) => {
            setEdited(true);
            props.onChange(e.target.value);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
              e.preventDefault();
              props.onAsk();
            }
          }}
        />
      </div>
      {showAsk && (
      <div className="ask-row">
        <button type="button" className="ask" onClick={props.onAsk}>
          Ask
        </button>
        <kbd>Ctrl+Enter</kbd>
      </div>
      )}
    </div>
  );
}

/** The regex pattern, collapsed: the verdict is what the room reads; the pattern is there to inspect or edit. */
export function Pattern(props: { label: string; children: ReactNode }) {
  const { presenting } = useDemo();
  if (presenting) return null;
  return (
    <details className="pattern">
      <summary>{props.label}</summary>
      {props.children}
    </details>
  );
}

/** The plain-English question Jev is asked, shown above its answer. */
export function JevQuestion(props: { children: ReactNode }) {
  return (
    <p className="jev-question" data-testid="jev-question">
      {props.children}
    </p>
  );
}

/** Editable `label: /pattern/flags` rules; reports the parse so callers can use the rules. */
export function RulesEditor(props: { value: string; onChange: (v: string) => void; label?: string }) {
  const id = useId();
  const parsed = parseRules(props.value);
  return (
    <div className="field">
      <label htmlFor={id}>{props.label ?? "Pattern"}</label>
      <textarea
        id={id}
        className="code"
        spellCheck={false}
        value={props.value}
        rows={Math.max(2, props.value.split("\n").length)}
        onChange={(e) => props.onChange(e.target.value)}
      />
      {parsed.kind === "error" && (
        <p className="error-text" role="alert">
          Line {parsed.line}: {parsed.message}
        </p>
      )}
    </div>
  );
}

/** Text with spans marked; overlapping spans are not supported (regex matches don't overlap). */
function Marked(props: { text: string; spans: readonly Mark[] }) {
  const sorted = [...props.spans].sort((a, b) => a.start - b.start);
  const parts: ReactNode[] = [];
  let at = 0;
  for (const [i, s] of sorted.entries()) {
    if (s.start < at) continue;
    if (s.start > at) parts.push(props.text.slice(at, s.start));
    parts.push(
      <mark key={i} className={s.className ?? "hit-regex"} title={s.title}>
        {props.text.slice(s.start, s.end)}
      </mark>,
    );
    at = s.end;
  }
  parts.push(props.text.slice(at));
  return <>{parts}</>;
}

export function Verdict(props: { correct: boolean | undefined }) {
  if (props.correct === undefined) return null;
  return props.correct ? (
    <span className="verdict ok" aria-label="matches the expected answer">
      ✓
    </span>
  ) : (
    <span className="verdict bad" aria-label="does not match the expected answer">
      ✗
    </span>
  );
}

export function Answer(props: { label: string; correct: boolean | undefined; detail?: ReactNode }) {
  return (
    <div className="answer">
      <span className="answer-label">{props.label}</span>
      <Verdict correct={props.correct} />
      {props.detail && <span className="answer-detail">{props.detail}</span>}
    </div>
  );
}

export function ProbBars(props: { rows: readonly { label: string; p: number; chosen?: boolean; tone?: "yes" | "review" | "no" }[] }) {
  return (
    <ul className="bars">
      {props.rows.map((r) => (
        <li key={r.label} className={[r.chosen ? "chosen" : "", r.tone ? `tone-${r.tone}` : ""].join(" ").trim()}>
          <span className="bar-label">{r.label}</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${Math.round(r.p * 100)}%` }} />
          </span>
          <span className="bar-value">{r.p.toFixed(2)}</span>
        </li>
      ))}
    </ul>
  );
}

export function Slider(props: { label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number }) {
  const id = useId();
  const { presenting } = useDemo();
  if (presenting) return null;
  return (
    <div className="slider">
      <label htmlFor={id}>{props.label}</label>
      <input
        id={id}
        type="range"
        min={props.min ?? 0}
        max={props.max ?? 1}
        step={props.step ?? 0.01}
        value={props.value}
        onChange={(e) => props.onChange(Number(e.target.value))}
      />
      <output htmlFor={id}>{props.value.toFixed(2)}</output>
    </div>
  );
}

type OkResult = Extract<JevResult, { kind: "ok" }>;

function formatUsd(usd: number): string {
  return usd < 0.0001 ? `$${usd.toFixed(6)}` : `$${usd.toFixed(4)}`;
}

/** Model, tokens, cost and latency of one answer. */
function UsageFooter(props: { result: OkResult }) {
  const { response, latencyMs, source, recordedAt } = props.result;
  const tokens = response.usage.input_tokens;
  const cost = costUsd(tokens);
  return (
    <footer className="usage" data-testid="usage">
      <span>{response.model}</span>
      <span>{tokens === null ? "tokens n/a" : `${tokens} input tokens`}</span>
      <span>{cost === null ? "cost n/a" : formatUsd(cost)}</span>
      <span>
        {latencyMs} ms{source === "recorded" ? " when recorded" : ""}
      </span>
      <span className={`source source-${source}`}>
        {source === "recorded" ? `recorded ${recordedAt?.slice(0, 10) ?? ""}` : "live"}
      </span>
    </footer>
  );
}

function CopyButton(props: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="copy"
      onClick={() => {
        void navigator.clipboard.writeText(props.text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

/** The exact request, the raw response, and the SDK call, collapsed by default. */
export function JevDetails(props: { result: JevResult }) {
  const { result } = props;
  const { presenting } = useDemo();
  const request = result.kind === "ok" || result.kind === "not_recorded" ? result.request : null;
  if (!request || presenting) return null;
  const code = sdkSnippet(request);
  return (
    <div className="details">
      <details>
        <summary>Request</summary>
        <pre data-testid="request-json">{JSON.stringify(request, null, 2)}</pre>
      </details>
      {result.kind === "ok" && (
        <details>
          <summary>Response</summary>
          <UsageFooter result={result} />
          <pre>{JSON.stringify(result.response, null, 2)}</pre>
        </details>
      )}
      <details>
        <summary>Code</summary>
        <CopyButton text={code} />
        <pre>{code}</pre>
      </details>
    </div>
  );
}

/**
 * The questions Jev is asked, editable in live mode: the counterpart of editing the regex.
 * Option names stay fixed; only the question and option descriptions change.
 */
export function MeaningEditor(props: { jev: Jev }) {
  const { mode, presenting } = useDemo();
  const { wording, setWording, defaultWording } = props.jev;
  const locked = mode !== "live";
  const edited = JSON.stringify(wording) !== JSON.stringify(defaultWording);
  const update = (key: string, entry: WordingEntry) => setWording({ ...wording, [key]: entry });
  if (presenting) return null;
  return (
    <details className="meaning" open={edited || undefined}>
      <summary>
        Full wording {edited && <span className="band band-review">edited</span>}
      </summary>
      {locked && <p className="muted small">Recorded answers use this wording. Switch to Live to edit it.</p>}
      {Object.entries(wording).map(([key, entry]) => (
        <fieldset key={key} disabled={locked}>
          <legend>
            <code>{key}</code>
          </legend>
          <textarea
            aria-label={`${key} question`}
            value={entry.instructions}
            rows={2}
            onChange={(e) => update(key, { ...entry, instructions: e.target.value })}
          />
          {entry.criteria &&
            Object.entries(entry.criteria).map(([option, description]) => (
              <label key={option} className="criterion">
                <code>{/^\d+$/.test(option) ? `level ${option}` : option}</code>
                <input
                  type="text"
                  value={description ?? ""}
                  onChange={(e) => update(key, { ...entry, criteria: { ...entry.criteria, [option]: e.target.value } })}
                />
              </label>
            ))}
        </fieldset>
      ))}
      {edited && (
        <button type="button" className="copy" onClick={() => setWording(defaultWording)}>
          Reset to recorded wording
        </button>
      )}
    </details>
  );
}

/** Renders loading / not-recorded / error states, or the station's own view of an answer. */
export function JevOutcome(props: { result: JevResult; children: (ok: OkResult) => ReactNode }) {
  const { result } = props;
  switch (result.kind) {
    case "idle":
      return <p className="muted">Pick an example or press Ask.</p>;
    case "loading":
      return <p className="muted">Asking Jev…</p>;
    case "not_recorded":
      return (
        <p className="notice" data-testid="not-recorded">
          Not recorded. Switch to Live to ask Jev about this text.
        </p>
      );
    case "error":
      return (
        <p className="error-text" role="alert" data-testid="jev-error">
          <strong>{result.errorKind}</strong>: {result.message}
        </p>
      );
    case "ok":
      return (
        <div className="jev-answer" data-testid="jev-answer" data-source={result.source}>
          {props.children(result)}
        </div>
      );
    default: {
      const _exhaustive: never = result;
      return _exhaustive;
    }
  }
}
