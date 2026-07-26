import { AnamEvent, createClient, type AnamClient } from "@anam-ai/js-sdk";

export type LiveClient = AnamClient;

export function createAnamClient(sessionToken: string): LiveClient {
  return createClient(sessionToken, {
    // Slightly snappier end-of-speech so Mini App turns feel responsive.
    voiceDetection: { endOfSpeechSensitivity: 0.65 },
  });
}

export { AnamEvent };
