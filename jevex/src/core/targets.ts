import type { JevRequest } from "./jev.ts";
import { STATIONS } from "./stations/index.ts";

/** A request the demo must have a recording for, and how many repeats to keep. */
export type RecordingTarget = { readonly label: string; readonly request: JevRequest; readonly repeats: number };

/** Every preset of every station, with default wording, for the pinned model. */
export function presetTargets(model: string): RecordingTarget[] {
  const out: RecordingTarget[] = [];
  for (const station of Object.values(STATIONS)) {
    for (const [i, raw] of station.presetInputs.entries()) {
      const built = station.build({ raw, wording: station.defaultWording, model });
      if (built.kind === "error") throw new Error(`Preset ${station.id}#${i} does not build: ${built.message}`);
      out.push({ label: `${station.id} preset ${i}`, request: built.request, repeats: 1 });
    }
  }
  return out;
}
