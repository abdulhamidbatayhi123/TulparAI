/**
 * Web Speech API wrapper — browser-native, free, Turkish-supported.
 *
 * Works in Chrome / Edge / Safari (incl. mobile). Firefox has limited support.
 * No backend round-trip — runs entirely in the browser via the OS / cloud
 * STT the browser ships with.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
type SpeechRecognitionType = any;
declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionType;
    webkitSpeechRecognition?: SpeechRecognitionType;
  }
}

export type VoiceHandle = {
  stop: () => void;
};

export function isVoiceSupported(): boolean {
  if (typeof window === "undefined") return false;
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

/**
 * Start listening. Calls `onPartial(text)` continuously with interim hypothesis,
 * `onFinal(text)` once recognition finalises, and `onError(msg)` on failure.
 * Returns a handle whose .stop() halts recognition early.
 */
export function startVoice({
  lang = "tr-TR",
  onPartial,
  onFinal,
  onError,
  onEnd,
}: {
  lang?: "tr-TR" | "en-US";
  onPartial?: (text: string) => void;
  onFinal?: (text: string) => void;
  onError?: (msg: string) => void;
  onEnd?: () => void;
}): VoiceHandle | null {
  const Ctor =
    (typeof window !== "undefined" &&
      (window.SpeechRecognition || window.webkitSpeechRecognition)) ||
    null;
  if (!Ctor) {
    onError?.("Tarayıcınız sesli giriş desteklemiyor (Chrome / Edge / Safari önerilir).");
    return null;
  }

  const recog: any = new Ctor();
  recog.lang = lang;
  recog.continuous = false;        // single utterance at a time
  recog.interimResults = true;     // emit partials as the user speaks
  recog.maxAlternatives = 1;

  recog.onresult = (event: any) => {
    let finalText = "";
    let partialText = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      const transcript = res[0].transcript;
      if (res.isFinal) finalText += transcript;
      else partialText += transcript;
    }
    if (partialText && onPartial) onPartial(partialText.trim());
    if (finalText && onFinal) onFinal(finalText.trim());
  };

  recog.onerror = (event: any) => {
    onError?.(`Sesli giriş hatası: ${event.error || "bilinmeyen"}`);
  };

  recog.onend = () => {
    onEnd?.();
  };

  try {
    recog.start();
  } catch (e) {
    onError?.(`Sesli giriş başlatılamadı: ${e instanceof Error ? e.message : String(e)}`);
    return null;
  }

  return {
    stop: () => {
      try {
        recog.stop();
      } catch {
        /* ignore */
      }
    },
  };
}
