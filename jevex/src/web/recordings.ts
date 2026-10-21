import { parseRecordings, RecordingStore } from "../core/recording.ts";
import raw from "../recordings/recordings.jsonl?raw";

/** All recorded answers, bundled into the app so recorded mode needs no server. */
export const recordings = new RecordingStore(parseRecordings(raw));
