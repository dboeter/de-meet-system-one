import { corpusTargets, type CorpusItem } from "./eval.ts";
import { presetTargets, type RecordingTarget } from "./targets.ts";

/** Everything the demo replays: every preset, and every labelled corpus item. */
export function allTargets(model: string, corpus: readonly CorpusItem[]): RecordingTarget[] {
  return [...presetTargets(model), ...corpusTargets(corpus, model)];
}
