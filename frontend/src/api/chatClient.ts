import type { ChatMessage, ChatRequest, ModelCatalogEntry, StreamChunk } from "../types/chat";

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * Fetch the model catalog the backend currently has credentials for.
 *
 * @returns The enabled catalog entries, in the order the backend returns them.
 */
export async function fetchModelCatalog(): Promise<ModelCatalogEntry[]> {
  const response = await fetch(`${API_BASE_URL}/api/models`);
  if (!response.ok) {
    throw new Error(`Model catalog request failed: ${response.status}`);
  }
  return (await response.json()) as ModelCatalogEntry[];
}

/**
 * Stream a companion reply for the given conversation.
 *
 * Uses `fetch` + a manually-parsed `ReadableStream` rather than `EventSource`,
 * since the backend needs a POST with a JSON body (the conversation history),
 * which `EventSource` cannot express.
 *
 * @param messages - Full conversation so far, ending with the latest user turn.
 * @param modelId - `ModelCatalogEntry.id` to reply with. Omit to let the
 *   backend fall back to persona-mode routing / its configured default.
 * @param signal - Optional abort signal to cancel an in-flight generation.
 * @yields Each `StreamChunk` sent by the backend, in order.
 */
export async function* streamChatReply(
  messages: ChatMessage[],
  modelId?: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, model_id: modelId } satisfies ChatRequest),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Chat request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? ""; // last element may be a partial event

    for (const rawEvent of events) {
      const line = rawEvent.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice("data:".length).trim();
      yield JSON.parse(payload) as StreamChunk;
    }
  }
}
