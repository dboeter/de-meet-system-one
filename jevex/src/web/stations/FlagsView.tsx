import { useEffect, useState } from "react";
import { parseRules } from "../../core/regex.ts";
import { FLAGS, flags, flagsRegex, readFlags, type Flag, type FlagsPreset } from "../../core/stations/flags.ts";
import type { BandThresholds } from "../../core/thresholds.ts";
import { Columns, EmailInput, Highlighted, JevDetails, JevOutcome, MeaningEditor, PresetChips, RulesEditor, StationHeader, Verdict } from "../components.tsx";
import { useJev } from "../useJev.ts";
import { startPreset, type ViewProps } from "../start.ts";

const BAND_LABEL = { yes: "yes", review: "review", no: "no" } as const;

export function FlagsView(props: ViewProps) {
  const initial = startPreset(flags.presets, props.start);
  const [text, setText] = useState(initial?.text ?? "");
  const [preset, setPreset] = useState<FlagsPreset | undefined>(initial);
  const [rulesText, setRulesText] = useState<string>(flags.defaultRules);
  const [thresholds, setThresholds] = useState<Readonly<Record<Flag, BandThresholds>>>(flags.defaultThresholds);
  const jev = useJev(flags);

  useEffect(() => {
    if (initial) jev.run({ text: initial.text });
  }, []); // once on mount; later runs come from preset clicks and Ask

  const gold = preset && preset.text === text ? preset.gold : undefined;
  const rules = parseRules(rulesText);
  const hits = rules.kind === "ok" ? flagsRegex(rules.rules, text) : null;

  const setThreshold = (flag: Flag, key: keyof BandThresholds, v: number) =>
    setThresholds((t) => {
      const cur = t[flag];
      // Keep no ≤ yes so the review band never inverts.
      const next = key === "no" ? { no: Math.min(v, cur.yes), yes: cur.yes } : { no: cur.no, yes: Math.max(v, cur.no) };
      return { ...t, [flag]: next };
    });

  return (
    <>
      <StationHeader
        title="Flags"
        code="noul × 5"
        blurb="Several things can be true of one email. One request asks five yes/no questions; each has its own review band, and moving a slider never asks Jev again."
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
          <>
            <EmailInput value={text} onChange={setText} onAsk={() => jev.run({ text })} />
            {gold && preset && (
              <p className="gold">
                Expected: <strong>{FLAGS.filter((f) => gold[f]).join(", ") || "no flags"}</strong>. {preset.note}
              </p>
            )}
          </>
        }
        regex={
          <>
            <RulesEditor value={rulesText} onChange={setRulesText} label="One pattern per flag" />
            {hits && (
              <>
                <ul className="flag-list">
                  {FLAGS.map((f) => (
                    <li key={f}>
                      <code>{f}</code>
                      <span className={hits[f] ? "flag-on" : "flag-off"}>{hits[f] ? "yes" : "no"}</span>
                      <Verdict correct={gold ? Boolean(hits[f]) === gold[f] : undefined} />
                    </li>
                  ))}
                </ul>
                <Highlighted text={text} spans={FLAGS.flatMap((f) => (hits[f] ? [{ ...hits[f], title: f }] : []))} />
              </>
            )}
          </>
        }
        jev={
          <>
          <JevOutcome result={jev.result}>
            {(ok) => (
              <ul className="flag-list jev-flags">
                {readFlags(ok.response, thresholds).map((r) => (
                  <li key={r.flag} className={`band-${r.band}`} data-testid={`flag-${r.flag}`}>
                    <div className="flag-head">
                      <code>{r.flag.replaceAll("_", "_\u200b")}</code>
                      <span className="flag-p">{r.p.toFixed(2)}</span>
                      <span className={`band band-${r.band}`}>{BAND_LABEL[r.band]}</span>
                      {/* A review answer is neither right nor wrong: a person decides. */}
                      <Verdict correct={gold && r.band !== "review" ? (r.band === "yes") === gold[r.flag] : undefined} />
                    </div>
                    <span className="bar-track">
                      <span className="bar-fill" style={{ width: `${Math.round(r.p * 100)}%` }} />
                    </span>
                    <div className="band-sliders">
                      <label>
                        no ≤
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.01}
                          value={thresholds[r.flag].no}
                          aria-label={`${r.flag} no threshold`}
                          onChange={(e) => setThreshold(r.flag, "no", Number(e.target.value))}
                        />
                        <output>{thresholds[r.flag].no.toFixed(2)}</output>
                      </label>
                      <label>
                        yes ≥
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.01}
                          value={thresholds[r.flag].yes}
                          aria-label={`${r.flag} yes threshold`}
                          onChange={(e) => setThreshold(r.flag, "yes", Number(e.target.value))}
                        />
                        <output>{thresholds[r.flag].yes.toFixed(2)}</output>
                      </label>
                    </div>
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
