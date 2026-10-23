import { useEffect, useState } from "react";
import { parseRules } from "../../core/regex.ts";
import { route, triage, triageRegex, type TriagePath, type TriagePreset, type TriageThresholds } from "../../core/stations/triage.ts";
import { Answer, Columns, EmailInput, JevDetails, JevOutcome, JevQuestion, MeaningEditor, Pattern, PresetChips, ProbBars, RulesEditor, Slider, StationHeader, Verdict } from "../components.tsx";
import { useDemo } from "../demo.tsx";
import { useJev } from "../useJev.ts";
import { startPreset, type ViewProps } from "../start.ts";

function PathBox(props: { path: TriagePath; urgent: boolean }) {
  const { path } = props;
  if (path.kind === "manual") {
    return (
      <div className="path path-manual" data-testid="triage-path">
        <div className="path-title">Manual triage</div>
        <div className="muted">Not sure enough to route; best guess {path.best}. A person decides.</div>
      </div>
    );
  }
  return (
    <div className="path path-auto" data-testid="triage-path">
      <div className="path-title">
        Auto-route to <strong>{path.team}</strong>
        {props.urgent && <span className="band band-yes">urgent</span>}
      </div>
      {path.copies.length > 0 && <div>Copy to {path.copies.join(", ")}</div>}
      {path.issue && (
        <div className="muted">
          {path.issue.question}: <code>{path.issue.label}</code> ({path.issue.p.toFixed(2)})
        </div>
      )}
    </div>
  );
}

export function TriageView(props: ViewProps) {
  const initial = startPreset(triage.presets, props.start);
  const [text, setText] = useState(initial?.text ?? "");
  const [preset, setPreset] = useState<TriagePreset | undefined>(initial);
  const [rulesText, setRulesText] = useState<string>(triage.defaultRules);
  const [urgencyText, setUrgencyText] = useState<string>(triage.defaultUrgencyRule);
  const [t, setT] = useState<TriageThresholds>(triage.defaultThresholds);
  const { presenting } = useDemo();
  const jev = useJev(triage);

  useEffect(() => {
    if (initial) jev.run({ text: initial.text });
  }, []); // once on mount; later runs come from preset clicks and Ask

  const gold = preset && preset.text === text ? preset.gold : undefined;
  const rules = parseRules(rulesText);
  const urgencyRules = parseRules(urgencyText);
  const regex = rules.kind === "ok" && urgencyRules.kind === "ok" ? triageRegex({ routing: rules.rules, urgency: urgencyRules.rules, text }) : null;

  return (
    <>
      <StationHeader
        title="Triage"
        code="choice + score"
        blurb="Route the email the way a support system would. One request asks the team, the urgency, and the follow-up for each team; code reads only the branch that applies, and confidence decides whether a person looks first."
      />
      <PresetChips
        presets={triage.presets}
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
            marks={regex ? [regex.departmentSpan, regex.urgentSpan].flatMap((s) => (s ? [s] : [])) : []}
          />
        }
        note={
          gold &&
          preset && (
            <p className="gold">
              Expected: <strong>{gold.department}</strong>
              {gold.urgent ? ", urgent" : ", not urgent"}. {preset.note}
            </p>
          )
        }
        regex={
          <>
            <p className="regex-kind">Routing table and an urgency rule</p>
            {regex && (
              <>
                {/* No matching row falls through to the catch-all team, as the eval scores it. */}
                <Answer
                  label={regex.department === "none" ? "none → other" : regex.department}
                  correct={gold ? (regex.department === "none" ? "other" : regex.department) === gold.department : undefined}
                  detail={regex.departmentSpan ? `saw “${regex.departmentSpan.text}”` : "no row matched"}
                />
                <div className="answer-line">
                  {regex.urgent ? "urgent" : "not urgent"} <Verdict correct={gold ? regex.urgent === gold.urgent : undefined} />
                </div>
              </>
            )}
            <Pattern label="Patterns">
              <RulesEditor value={rulesText} onChange={setRulesText} label="Routing table" />
              <RulesEditor value={urgencyText} onChange={setUrgencyText} label="Urgency rule" />
            </Pattern>
          </>
        }
        jev={
          <>
          <JevQuestion>
            {jev.wording.department?.instructions} {jev.wording.urgency?.instructions}
          </JevQuestion>
          <JevOutcome result={jev.result}>
            {(ok) => {
              const r = route(ok.response, t);
              const team = r.path.kind === "auto" ? r.path.team : null;
              return (
                <>
                  <PathBox path={r.path} urgent={r.urgent} />
                  <div className="answer-line">
                    team <Verdict correct={gold && team !== null ? team === gold.department : undefined} /> · urgency{" "}
                    {r.urgency.toFixed(2)} / 2 <Verdict correct={gold ? r.urgent === gold.urgent : undefined} />
                  </div>
                  <ProbBars rows={r.departments.map((d) => ({ ...d, chosen: d.label === team }))} />
                  <Slider label="Route if confidence ≥" value={t.minConfidence} onChange={(v) => setT({ ...t, minConfidence: v })} />
                  {!presenting && <div className="muted small">department confidence {r.confidence.toFixed(2)}</div>}
                  <Slider label="Copy team if p >" value={t.copyAbove} onChange={(v) => setT({ ...t, copyAbove: v })} />
                  <Slider label="Urgent if score ≥" value={t.urgentAt} min={0} max={2} onChange={(v) => setT({ ...t, urgentAt: v })} />
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
