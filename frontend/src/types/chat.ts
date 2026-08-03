// Mirrors of backend Pydantic models in backend/src/models/chat.py.
// Keep these two in sync by hand for now — no shared schema/codegen in this increment.

export enum ChatRole {
  User = "user",
  Assistant = "assistant",
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
  /** Frontend-only display field for an auto-generated image reply; never sent to the backend. */
  imageUrl?: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  model_id?: string;
}

export enum StreamChunkType {
  Token = "token",
  Image = "image",
  Done = "done",
  Error = "error",
}

export interface StreamChunk {
  type: StreamChunkType;
  content: string | null;
}

// Mirrors backend/src/config.py::ModelCatalogEntry.
export interface ModelCatalogEntry {
  id: string;
  provider_id: string;
  model: string;
  display_name: string;
  cost_tier: "free" | "paid";
  uncensored: boolean;
  enabled: boolean;
}
