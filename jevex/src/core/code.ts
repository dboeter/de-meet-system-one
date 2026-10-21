import type { JevRequest } from "./jev.ts";

/** The SDK call that sends `request`, ready to paste into a Node 22+ ES module. */
export function sdkSnippet(request: JevRequest): string {
  return `import { TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient(); // reads TYPESAFE_API_KEY
const response = await client.systemOne(${JSON.stringify(request, null, 2)});
console.log(JSON.stringify(response.answers, null, 2));
`;
}
