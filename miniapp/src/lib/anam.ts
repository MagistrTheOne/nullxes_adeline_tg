import { AnamEvent, createClient, type AnamClient } from "@anam-ai/js-sdk";

export type LiveClient = AnamClient;

export function createAnamClient(sessionToken: string): LiveClient {
  return createClient(sessionToken);
}

export { AnamEvent };
