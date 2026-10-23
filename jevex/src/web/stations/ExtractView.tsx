import { useEffect, useState } from "react";
import { choiceOf, ranked } from "../../core/jev.ts";
import { extract, findCandidates, KINDS, NONE, readPick, type ExtractPreset, type Kind } from "../../core/stations/extract.ts";
import { Answer, Columns, EmailInput, JevDetails, JevOutcome, JevQuestion, MeaningEditor, Pattern, PresetChips, ProbBars, RulesEditor, StationHeader } from "../components.tsx";
import { useDemo } from "../demo.tsx";
import { useJev, type JevResult } from "../useJev.ts";
import { startPreset, type ViewProps } from "../start.ts";

/** Jev's pick and its probability, checked against the options that were sent, not the ones Jev echoed back. */
function pickOf(ok: Extract<JevResult, { kind: "ok" }>): { value: string; p: number } {
  const q = ok.request.questions.pick;
  const candidates = q?.type === "choice" ? Object.keys(q.criteria).filter((c) => c !== NONE) : [];
  const pick = readPick(ok.response, candidates);
  return { value: pick.kind === "picked" ? pick.value : "none", p: pick.p };
}

export function ExtractView(props: ViewProps) {
  const initial = startPreset(extract.presets, props.start);
  const [kind, setKind] = useState<Kind>(initial?.kind ?? "order");
  const [text, setText] = useState(initial?.text ?? "");
  const [preset, setPreset] = useState<ExtractPreset | undefined>(initial);
  const [finders, setFinders] = useState<Readonly<Record<Kind, string>>>(extract.finders);
  const [skipped, setSkipped] = useState(false);
  const jev = useJev(extract);
  const { presenting } = useDemo();

  const found = findCandidates(finders[kind], text);

  const ask = (k: Kind, t: string, finder: string) => {
    const candidates = findCandidates(finder, t).candidates;
    // No candidates, no question: Jev can only choose among spans the regex found.
    setSkipped(candidates.length === 0);
    if (candidates.length > 0) jev.run({ kind: k, text: t, candidates });
  };

  useEffect(() => {
    if (initial) ask(initial.kind, initial.text, extract.finders[initial.kind]);
  }, []); // once on mount; later runs come from preset clicks and Ask

  const gold = preset && preset.text === text && preset.kind === kind ? preset.gold : undefined;
  const regexPick = found.candidates[0];
  const jevPick = !skipped && jev.result.kind === "ok" ? pickOf(jev.result).value : null;
  const question = extract.defaultWording[kind]?.instructions ?? kind;

  return (
    <>
      <StationHeader
        title="Keep your regex"
        code="regex + choice"
        blurb="The regex you trust finds the candidates; Jev picks the one the question asks for. The answer is always one of the highlighted spans, copied unchanged: it can be wrong, but never invented."
      />
      <PresetChips
        presets={extract.presets}
        selected={gold ? (preset?.id ?? null) : null}
        onPick={(p) => {
          setPreset(p);
          setKind(p.kind);
          setText(p.text);
          ask(p.kind, p.text, finders[p.kind]);
        }}
      />
      <Columns
        input={
          <EmailInput
            value={text}
            onChange={setText}
            onAsk={() => ask(kind, text, finders[kind])}
            label="Text"
            marks={found.spans.map((s) => (s.text === jevPick ? { ...s, className: "hit-jev" } : s))}
          />
        }
        note={
          gold &&
          preset && (
            <p className="gold">
              Expected: <strong>{gold}</strong>. {preset.note}
            </p>
          )
        }
        regex={
          <>
            <p className="regex-kind">
              Finds {found.candidates.length} candidate{found.candidates.length === 1 ? "" : "s"}; takes the first
            </p>
            <Answer label={regexPick ?? "no match"} correct={gold === undefined ? undefined : regexPick === gold} />
            <Pattern label="Finder">
              <RulesEditor value={finders[kind]} onChange={(v) => setFinders({ ...finders, [kind]: v })} label="Finder" />
            </Pattern>
          </>
        }
        jev={
          <>
          {presenting ? (
            <JevQuestion>{question}</JevQuestion>
          ) : (
            <div className="field jev-question">
              <select aria-label="Question" value={kind} onChange={(e) => setKind(KINDS.find((k) => k === e.target.value) ?? "order")}>
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {extract.defaultWording[k]?.instructions ?? k}
                  </option>
                ))}
              </select>
            </div>
          )}
          {skipped ? (
            <p className="notice" data-testid="no-candidates">
              The finder found no candidates, so there is nothing for Jev to pick from. Jev was not asked.
            </p>
          ) : (
            <JevOutcome result={jev.result}>
              {(ok) => {
                const { value, p } = pickOf(ok);
                return (
                  <>
                    <Answer label={value} correct={gold === undefined ? undefined : value === gold} detail={`p ${p.toFixed(2)}`} />
                    <ProbBars rows={ranked(choiceOf(ok.response, "pick")).map((r) => ({ ...r, chosen: r.label === value }))} />
                  </>
                );
              }}
            </JevOutcome>
          )}
          <MeaningEditor jev={jev} />
          </>
        }
        below={<JevDetails result={jev.result} />}
      />
    </>
  );
}
