import { useEffect, useState } from "react";
import { parseRules } from "../../core/regex.ts";
import { readScan, scan, scanRegex, splitSentences, type ScanPreset } from "../../core/stations/scan.ts";
import { Columns, EmailInput, Highlighted, JevDetails, JevOutcome, MeaningEditor, PresetChips, RulesEditor, Slider, StationHeader, Verdict } from "../components.tsx";
import { useJev } from "../useJev.ts";
import { startPreset, type ViewProps } from "../start.ts";

export function ScanView(props: ViewProps) {
  const initial = startPreset(scan.presets, props.start);
  const [text, setText] = useState(initial?.text ?? "");
  const [preset, setPreset] = useState<ScanPreset | undefined>(initial);
  const [rulesText, setRulesText] = useState<string>(scan.defaultRules);
  const [threshold, setThreshold] = useState<number>(scan.defaultThreshold);
  const jev = useJev(scan);

  useEffect(() => {
    if (initial) jev.run({ text: initial.text });
  }, []); // once on mount; later runs come from preset clicks and Ask

  const sentences = splitSentences(text);
  const gold = preset && preset.text === text ? preset.gold : undefined;
  const rules = parseRules(rulesText);
  const hits = rules.kind === "ok" ? scanRegex(rules.rules, sentences) : null;

  return (
    <>
      <StationHeader
        title="Scan"
        code="noul per sentence"
        blurb="Which sentences in a long email need action? Code splits the sentences; one request asks a yes/no question per sentence. Slide the threshold: the answers are already in, so nothing is asked again."
      />
      <PresetChips
        presets={scan.presets}
        selected={gold ? (preset?.id ?? null) : null}
        onPick={(p) => {
          setPreset(p);
          setText(p.text);
          jev.run({ text: p.text });
        }}
      />
      <Columns
        input={
          <>
            <EmailInput value={text} onChange={setText} onAsk={() => jev.run({ text })} rows={8} />
            {gold && preset && <p className="gold">{preset.note}</p>}
          </>
        }
        regex={
          <>
            <RulesEditor value={rulesText} onChange={setRulesText} label="Problem words" />
            {hits && (
              <>
                <ul className="sentences">
                  {hits.map((h, i) => (
                    <li key={h.span.start} className={h.hit ? "on-regex" : ""}>
                      <span className="sentence-text">{h.span.text}</span>
                      <Verdict correct={gold?.[i] === undefined ? undefined : Boolean(h.hit) === gold[i]} />
                    </li>
                  ))}
                </ul>
                <Highlighted text={text} spans={hits.flatMap((h) => (h.hit ? [h.hit] : []))} />
              </>
            )}
          </>
        }
        jev={
          <>
          <JevOutcome result={jev.result}>
            {(ok) => {
              const state = ok.request.state;
              // Read the sentences that were sent, so a later edit to the text can't misalign them.
              const sent =
                typeof state === "object" && state !== null && !Array.isArray(state) && "email" in state && typeof state.email === "string"
                  ? splitSentences(state.email)
                  : sentences;
              const rows = readScan(ok.response, sent, threshold);
              return (
                <>
                  <Slider label="Threshold" value={threshold} onChange={setThreshold} />
                  <div className="answer-line">
                    {rows.filter((r) => r.needsAction).length} of {rows.length} sentences need action
                  </div>
                  <ul className="sentences">
                    {rows.map((r, i) => (
                      <li key={r.span.start} className={r.needsAction ? "on-jev" : ""} data-testid="scan-row">
                        <span className="flag-p">{r.p.toFixed(2)}</span>
                        <span className="sentence-text">{r.span.text}</span>
                        <Verdict correct={gold?.[i] === undefined ? undefined : r.needsAction === gold[i]} />
                        <span className="bar-track">
                          <span className="bar-fill" style={{ width: `${Math.round(r.p * 100)}%` }} />
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              );
            }}
          </JevOutcome>
          <MeaningEditor jev={jev} />
          </>
        }
        below={<JevDetails result={jev.result} />}
      />
    </>
  );
}
