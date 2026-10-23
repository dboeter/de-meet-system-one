import { useEffect, useState } from "react";
import { parseRules } from "../../core/regex.ts";
import { FLAGS, flags, flagsRegex, readFlags, type Flag, type FlagsPreset } from "../../core/stations/flags.ts";
import type { BandThresholds } from "../../core/thresholds.ts";
import { Columns, EmailInput, JevDetails, JevOutcome, JevQuestion, MeaningEditor, Pattern, PresetChips, RulesEditor, StationHeader, Verdict } from "../components.tsx";
import { useJev } from "../useJev.ts";
import { startPreset, type ViewProps } from "../start.ts";

const BAND_LABEL = { yes: "yes", review: "review", no: "no" } as const;

export function FlagsView(props: ViewProps) {
  const initial = startPreset(flags.presets, props.start);
  const [text, setText] = useState(initial?.text ?? "");
  const [preset, setPreset] = useState<FlagsPreset | undefined>(initial);
  const [rulesText, setRulesText] = useState<string>(flags.defaultRules);
  // One review band for all five flags; the defaults are the same for each.
  const band: BandThresholds = flags.defaultThresholds[FLAGS[0]];
  const thresholds = Object.fromEntries(FLAGS.map((f) => [f, band])) as Record<Flag, BandThresholds>;
  const jev = useJev(flags);

  useEffect(() => {
    if (initial) jev.run({ text: initial.text });
  }, []); // once on mount; later runs come from preset clicks and Ask

  const gold = preset && preset.text === text ? preset.gold : undefined;
  const rules = parseRules(rulesText);
  const hits = rules.kind === "ok" ? flagsRegex(rules.rules, text) : null;


  return (
    <>
      <StationHeader
        title="Flags"
        code="noul × 5"
        blurb="Several things can be true of one email. One request asks five yes/no questions; each answer lands in yes, review or no."
      />
      <PresetChips
        presets={flags.presets}
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
            marks={hits ? FLAGS.flatMap((f) => (hits[f] ? [{ ...hits[f], title: f }] : [])) : []}
          />
        }
        note={
          gold &&
          preset && (
            <p className="gold">
              Expected: <strong>{FLAGS.filter((f) => gold[f]).join(", ") || "no flags"}</strong>. {preset.note}
            </p>
          )
        }
        regex={
          <>
            <p className="regex-kind">One keyword pattern per flag</p>
            {hits && (
                <ul className="flag-list">
                  {FLAGS.map((f) => (
                    <li key={f}>
                      <code>{f}</code>
                      <span className={hits[f] ? "flag-on" : "flag-off"}>{hits[f] ? "yes" : "no"}</span>
                      <Verdict correct={gold ? Boolean(hits[f]) === gold[f] : undefined} />
                    </li>
                  ))}
                </ul>
            )}
            <Pattern label="Patterns">
              <RulesEditor value={rulesText} onChange={setRulesText} label="One pattern per flag" />
            </Pattern>
          </>
        }
        jev={
          <>
          <JevQuestion>Five yes/no questions in one request. Between the two thresholds, a person reviews.</JevQuestion>
          <JevOutcome result={jev.result}>
            {(ok) => (
              <ul className="flag-list jev-flags">
                {readFlags(ok.response, thresholds).map((r) => (
                  <li key={r.flag} className={`band-${r.band}`} data-testid={`flag-${r.flag}`}>
                    <div className="flag-head">
                      <code title={jev.wording[r.flag]?.instructions}>{r.flag.replaceAll("_", "_\u200b")}</code>
                      <span className="flag-p">{r.p.toFixed(2)}</span>
                      <span className={`band band-${r.band}`}>{BAND_LABEL[r.band]}</span>
                      {/* A review answer is neither right nor wrong: a person decides. */}
                      <Verdict correct={gold && r.band !== "review" ? (r.band === "yes") === gold[r.flag] : undefined} />
                    </div>
                    <span className="bar-track">
                      <span className="bar-fill" style={{ width: `${Math.round(r.p * 100)}%` }} />
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </JevOutcome>
          <MeaningEditor jev={jev} />
          </>
        }
        below={<JevDetails result={jev.result} />}
      />
    </>
  );
}
