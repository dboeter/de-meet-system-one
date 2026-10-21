import { extract } from "./extract.ts";
import { flags } from "./flags.ts";
import { intent } from "./intent.ts";
import { scan } from "./scan.ts";
import { triage } from "./triage.ts";
import type { StationDef, StationId } from "./station.ts";

export const STATIONS: Readonly<Record<StationId, StationDef>> = {
  intent,
  flags,
  triage,
  extract,
  scan,
};

export function stationById(id: unknown): StationDef | undefined {
  return typeof id === "string" && Object.hasOwn(STATIONS, id) ? STATIONS[id as StationId] : undefined;
}

export type { StationDef, StationId } from "./station.ts";
