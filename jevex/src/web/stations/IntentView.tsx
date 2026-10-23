import { useEffect, useState } from "react";
import { parseRules } from "../../core/regex.ts";
import { intent, intentRegexVerdict, readIntent, type IntentPreset } from "../../core/stations/intent.ts";
import { Answer, Columns, EmailInput, JevDetails, JevOutcome, JevQuestion, MeaningEditor, Pattern, PresetChips, ProbBars, RulesEditor, StationHeader } from "../components.tsx";
import { useJev } from "../useJev.ts";
import { startPreset, type ViewProps } from "../start.ts";

export function IntentView(props: ViewProps) {
  const initial = startPreset(intent.presets, props.start);
  const [text, setText] = useState(initial?.text ?? "");
  const [preset, setPreset] = useState<IntentPreset | undefined>(initial);
  const [rulesText, setRulesText] = useState<string>(intent.defaultRules);
  const jev = useJev(intent);

  // Answer the opening example straight away; recorded answers are instant.
  useEffect(() => {
    if (initial) jev.run({ text: initial.text });
  }, []); // once on mount; later runs come from preset clicks and Ask

  const gold = preset && preset.text === text ? preset.gold : undefined;
  const rules = parseRules(rulesText);
  const verdict = rules.kind === "ok" ? intentRegexVerdict(rules.rules, text) : null;

  return (
    <>
      <StationHeader
        title="Intent"
        code="choice"
        blurb="What does this customer want? The regex is a keyword ladder: first rule that matches wins. Jev picks one intent and gives a probability for each."
      />
      <PresetChips
        presets={intent.presets}
        selected={gold ? (preset?.id ?? null) : null}
        onPick={(p) => {
          setPreset(p);
          setText(p.text);
          jev.run({ text: p.text });
        }}
      />
      <Columns
        input={<EmailInput value={text} onChange={setText} onAsk={() => jev.run({ text })} marks={verdict?.span ? [verdict.span] : []} />}
        note={
          gold && (
            <p className="gold">
              Expected: <strong>{gold}</strong>. {preset?.note}
            </p>
          )
        }
        regex={
          <>
            <p className="regex-kind">Keyword ladder, first match wins</p>
            {verdict && (
              <Answer
                label={verdict.label}
                correct={gold === undefined ? undefined : verdict.label === gold}
                detail={verdict.span ? `saw “${verdict.span.text}”` : "no keyword"}
              />
            )}
            <Pattern label="Pattern">
              <RulesEditor value={rulesText} onChange={setRulesText} label="Keyword ladder" />
            </Pattern>
          </>
        }
        jev={
          <>
          <JevQuestion>{jev.wording.intent?.instructions}</JevQuestion>
          <JevOutcome result={jev.result}>
            {(ok) => {
              const reading = readIntent(ok.response);
              return (
                <>
                  <Answer
                    label={reading.label}
                    correct={gold === undefined ? undefined : reading.label === gold}
                    detail={`confidence ${reading.confidence.toFixed(2)}`}
                  />
                  <ProbBars rows={reading.ranked.map((r) => ({ ...r, chosen: r.label === reading.label }))} />
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
