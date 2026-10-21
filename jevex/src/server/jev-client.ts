import { APIConnectionError, APIError, TypeSafeClient, type SystemOneRequest } from "@typesafe-ai/sdk";
import type { JevRequest } from "../core/jev.ts";
import { JevCallError, type JevCaller } from "./api.ts";

/** A caller backed by the TypeSafe SDK, or `null` when no API key is set. */
export function createJevCaller(apiKey: string | undefined): JevCaller | null {
  if (!apiKey || apiKey.trim() === "") return null;
  const client = new TypeSafeClient({ apiKey });
  return async (request: JevRequest) => {
    try {
      // Our request type is the readonly JSON subset of the SDK's request type; the SDK's
      // own types are mutable, so the readonly arrays need this widening.
      return await client.systemOne(request as SystemOneRequest);
    } catch (e) {
      if (e instanceof APIError) throw new JevCallError("api_error", `${e.status}: ${e.message}`);
      if (e instanceof APIConnectionError) throw new JevCallError("connection_error", e.message);
      throw e;
    }
  };
}
