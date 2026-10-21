import type { ComponentType } from "react";
import type { ViewProps } from "./start.ts";
import { ExtractView } from "./stations/ExtractView.tsx";
import { FlagsView } from "./stations/FlagsView.tsx";
import { KeepRegexView } from "./stations/KeepRegexView.tsx";
import { IntentView } from "./stations/IntentView.tsx";
import { ScoreboardView } from "./stations/ScoreboardView.tsx";
import { ScanView } from "./stations/ScanView.tsx";
import { TriageView } from "./stations/TriageView.tsx";

export type ViewId = "intent" | "flags" | "triage" | "extract" | "scan" | "scoreboard" | "keep";

export type ViewDef = {
  readonly id: ViewId;
  readonly title: string;
  readonly code: string;
  readonly group: "Classify" | "Extract" | "Trust";
  /** Whether the screen has an email box, so `L` can open it blank as the live box. */
  readonly takesEmail: boolean;
  readonly View: ComponentType<ViewProps>;
};

/** Screens in nav order. */
export const VIEWS: readonly [ViewDef, ...ViewDef[]] = [
  { id: "intent", title: "Intent", code: "choice", group: "Classify", takesEmail: true, View: IntentView },
  { id: "flags", title: "Flags", code: "noul", group: "Classify", takesEmail: true, View: FlagsView },
  { id: "triage", title: "Triage", code: "choice+score", group: "Classify", takesEmail: true, View: TriageView },
  { id: "extract", title: "Keep your regex", code: "pick", group: "Extract", takesEmail: true, View: ExtractView },
  { id: "scan", title: "Scan", code: "noul/sentence", group: "Extract", takesEmail: true, View: ScanView },
  { id: "scoreboard", title: "Scoreboard", code: "eval", group: "Trust", takesEmail: false, View: ScoreboardView },
  { id: "keep", title: "When to keep the regex", code: "re", group: "Trust", takesEmail: false, View: KeepRegexView },
];

export function viewById(id: string): ViewDef | undefined {
  return VIEWS.find((v) => v.id === id);
}
