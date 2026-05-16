/**
 * Typed backend client for TulparAI.
 *
 * Backend: FastAPI at `NEXT_PUBLIC_BACKEND_URL` (default http://localhost:8000).
 *
 * The chat endpoint is Server-Sent Events; we consume it with `fetch` + a
 * streaming reader rather than the native `EventSource` because EventSource
 * doesn't support POST bodies.
 */

const BASE =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type Source = {
  marker: string;
  tool: string;
  text: string;
  url?: string;
  source_name?: string;
  page_number?: number;
};

export type ToolCall = {
  tool: string;
  args: Record<string, unknown>;
  ms: number;
};

export type ChatStreamEvent =
  | { type: "step"; step: number; name: string }
  | { type: "tool_call"; tool: string; args: Record<string, unknown>; summary: string; ms: number }
  | { type: "token"; content: string }
  | {
      type: "done";
      answer: string;
      sources: Source[];
      trace: ToolCall[];
      removed_claims?: string[];
      verification_score: number;
      latency_ms: number;
    }
  | { type: "error"; message: string };

/* -------------------------------------------------------------------------- */
/*  Simple JSON helpers                                                        */
/* -------------------------------------------------------------------------- */

export async function getHealth(): Promise<{
  status: string;
  service: string;
  models: Record<string, string>;
}> {
  const r = await fetch(`${BASE}/health`);
  if (!r.ok) throw new Error(`Health check failed (${r.status})`);
  return r.json();
}

export async function getProfile(athleteId: string) {
  const r = await fetch(`${BASE}/profile/${athleteId}`);
  if (!r.ok) throw new Error(`Profile ${athleteId} fetch failed (${r.status})`);
  return r.json();
}

export async function upsertProfile(profile: Record<string, unknown>) {
  const r = await fetch(`${BASE}/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!r.ok) throw new Error(`Profile upsert failed (${r.status}): ${await r.text()}`);
  return r.json() as Promise<{ ok: boolean; athlete_id: string }>;
}

export async function addLog(
  athleteId: string,
  type: "training" | "meal" | "weight" | "sleep",
  data: Record<string, unknown>
) {
  const r = await fetch(`${BASE}/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ athlete_id: athleteId, type, data }),
  });
  if (!r.ok) throw new Error(`Log failed (${r.status})`);
  return r.json();
}

/* -------------------------------------------------------------------------- */
/*  SSE chat                                                                   */
/* -------------------------------------------------------------------------- */

export type ChatPayload = {
  athlete_id: string;
  message: string;
  language?: "tr" | "en";
  /** Optional inline image — raw base64 (no `data:` prefix). Backend wraps it. */
  image_base64?: string;
};

/** Convert a File (from <input type="file">) into base64 string for the chat payload. */
export async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // strip the `data:image/...;base64,` prefix — backend re-wraps
      const comma = result.indexOf(",");
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

/**
 * Open the /chat/stream SSE.
 *
 * Returns a cancel function. Calling it aborts the request.
 *
 * `onEvent` is called for each parsed SSE event in order:
 *   - step:      pipeline progress (Analyzing/Reasoning/Verifying/Formatting)
 *   - tool_call: an individual tool invocation (name, args, summary, ms)
 *   - done:      final answer + sources + trace + verification_score
 *   - error:     any failure (network, server, or pipeline)
 */
export function openChatStream(
  payload: ChatPayload,
  onEvent: (e: ChatStreamEvent) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const r = await fetch(`${BASE}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!r.ok || !r.body) {
        const txt = await r.text().catch(() => "");
        onEvent({ type: "error", message: `HTTP ${r.status}: ${txt.slice(0, 200)}` });
        return;
      }

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        // SSE events are separated by a blank line (\n\n)
        const events = buf.split("\n\n");
        buf = events.pop() || "";

        for (const evt of events) {
          if (!evt.trim()) continue;
          for (const line of evt.split("\n")) {
            if (line.startsWith("data: ")) {
              const json = line.slice(6);
              try {
                onEvent(JSON.parse(json) as ChatStreamEvent);
              } catch {
                /* ignore malformed line */
              }
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      onEvent({
        type: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  })();

  return () => controller.abort();
}
