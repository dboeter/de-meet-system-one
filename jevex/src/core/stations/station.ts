import { isRecord } from "../guards.ts";
import { MAX_INPUT_CHARS } from "../config.ts";
import type { JevRequest } from "../jev.ts";
import type { Wording } from "../wording.ts";

export type StationId = "intent" | "flags" | "triage" | "extract" | "scan";

export type BuildResult =
  | { readonly kind: "ok"; readonly request: JevRequest }
  | { readonly kind: "error"; readonly reason: "invalid" | "too_long"; readonly message: string };

export type BuildArgs = { readonly raw: unknown; readonly wording: Wording; readonly model: string };

/** What the server, the record script and the UI need from every station. */
export interface StationDef {
  readonly id: StationId;
  readonly defaultWording: Wording;
  /** Validate raw client input and build the Jev request for it. */
  build(args: BuildArgs): BuildResult;
  /** The raw inputs of every preset, in display order. */
  readonly presetInputs: readonly unknown[];
}

export type TextCheck =
  | { readonly kind: "ok"; readonly text: string }
  | { readonly kind: "error"; readonly reason: "invalid" | "too_long"; readonly message: string };

/** Read `{text}` from raw input, enforcing the live-mode length cap. */
export function readText(raw: unknown): TextCheck {
  if (!isRecord(raw) || typeof raw.text !== "string" || raw.text.trim() === "") {
    return { kind: "error", reason: "invalid", message: "input.text must be non-empty text" };
  }
  if (raw.text.length > MAX_INPUT_CHARS) {
    return { kind: "error", reason: "too_long", message: `Text is longer than ${MAX_INPUT_CHARS} characters` };
  }
  return { kind: "ok", text: raw.text };
}
