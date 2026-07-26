/** Rewrite brand names for TTS so engines don't spell them letter-by-letter. */

const BRAND_SPEECH_RU = "Нуллксес";
const BRAND_SPEECH_EN = "Nullexes";

function looksRussian(text: string): boolean {
  return /[а-яё]/i.test(text);
}

/** Text for Anam / TTS. Caption UI should keep the original spelling. */
export function forSpeech(text: string): string {
  if (!text) return text;
  const spoken = looksRussian(text) ? BRAND_SPEECH_RU : BRAND_SPEECH_EN;
  return text
    .replace(/NULLXES/gi, spoken)
    .replace(/Nullxes/g, spoken);
}
