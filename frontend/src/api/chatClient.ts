import type {
  ChatMessage,
  ChatRequest,
  ImageCatalogEntry,
  ModelCatalogEntry,
  ModelSelection,
  StreamChunk,
  VideoCatalogEntry,
} from "../types/chat";

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
 * Fetch the catalog of models available for auto-detected image generation.
 *
 * Informational only — there is no per-request way to choose one of these
 * yet, generation always uses the backend's configured default.
 *
 * @returns The enabled image-generation catalog entries.
 */
export async function fetchImageModelCatalog(): Promise<ImageCatalogEntry[]> {
  const response = await fetch(`${API_BASE_URL}/api/models/images`);
  if (!response.ok) {
    throw new Error(`Image model catalog request failed: ${response.status}`);
  }
  return (await response.json()) as ImageCatalogEntry[];
}

/**
 * Fetch the catalog of models available for auto-detected video generation.
 *
 * Informational only — same caveat as `fetchImageModelCatalog`.
 *
 * @returns The enabled video-generation catalog entries.
 */
export async function fetchVideoModelCatalog(): Promise<VideoCatalogEntry[]> {
  const response = await fetch(`${API_BASE_URL}/api/models/videos`);
  if (!response.ok) {
    throw new Error(`Video model catalog request failed: ${response.status}`);
  }
  return (await response.json()) as VideoCatalogEntry[];
}

/**
 * Stream a companion reply for the given conversation.
 *
 * Uses `fetch` + a manually-parsed `ReadableStream` rather than `EventSource`,
 * since the backend needs a POST with a JSON body (the conversation history),
 * which `EventSource` cannot express.
 *
 * @param messages - Full conversation so far, ending with the latest user turn.
 * @param selection - Which backend to use per modality. Any omitted field
 *   defers to the backend's own routing / configured default.
 * @param signal - Optional abort signal to cancel an in-flight generation.
 * @yields Each `StreamChunk` sent by the backend, in order.
 */
export async function* streamChatReply(
  messages: ChatMessage[],
  selection: ModelSelection = {},
  signal?: AbortSignal,
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      model_id: selection.modelId,
      image_model_id: selection.imageModelId,
      video_model_id: selection.videoModelId,
    } satisfies ChatRequest),
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
