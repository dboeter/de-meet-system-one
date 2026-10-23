import { useEffect, useState } from "react";
import { parseRules } from "../../core/regex.ts";
import { readScan, scan, scanRegex, splitSentences, type ScanPreset } from "../../core/stations/scan.ts";
import { Answer, Columns, EmailInput, JevDetails, JevOutcome, JevQuestion, MeaningEditor, Pattern, PresetChips, RulesEditor, Slider, StationHeader, Verdict } from "../components.tsx";
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
  const flagged = hits?.filter((h) => h.hit).length ?? 0;
  // The question is asked per sentence by path; show it as it reads to a person.
  const question = (jev.wording.needs_action?.instructions ?? "").replace(/`sentences\[\{i\}\]`/, "this sentence").split("? ")[0];

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
          <EmailInput
            value={text}
            onChange={setText}
            onAsk={() => jev.run({ text })}
            rows={6}
            marks={hits ? hits.flatMap((h) => (h.hit ? [h.hit] : [])) : []}
          />
        }
        note={gold && preset && <p className="gold">{preset.note}</p>}
        regex={
          <>
            <p className="regex-kind">A sentence needs action if it has a problem word</p>
            {hits && (
              <Answer
                label={`${flagged} of ${hits.length}`}
                correct={gold ? hits.every((h, i) => gold[i] === undefined || Boolean(h.hit) === gold[i]) : undefined}
                detail={`sentence${flagged === 1 ? "" : "s"} flagged`}
              />
            )}
            <Pattern label="Pattern">
              <RulesEditor value={rulesText} onChange={setRulesText} label="Problem words" />
            </Pattern>
          </>
        }
        jev={
          <>
          <JevQuestion>{question}? Asked once per sentence, in one request.</JevQuestion>
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
