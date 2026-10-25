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
  /** Frontend-only display field for an auto-generated video reply; never sent to the backend. */
  videoUrl?: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  model_id?: string;
  image_model_id?: string;
  video_model_id?: string;
}

export enum StreamChunkType {
  Token = "token",
  Image = "image",
  Video = "video",
  Done = "done",
  Error = "error",
}

export interface StreamChunk {
  type: StreamChunkType;
  content: string | null;
}

// Mirrors backend/src/config.py::ModelCatalogEntry / ImageCatalogEntry /
// VideoCatalogEntry. The backend keeps those as three distinct Pydantic models
// because each carries a different `provider_id` enum; on the wire `provider_id`
// is just a string, so one shape covers all three here.
export interface CatalogEntry {
  id: string;
  provider_id: string;
  model: string;
  display_name: string;
  cost_tier: "free" | "paid";
  uncensored: boolean;
  enabled: boolean;
}

export type ModelCatalogEntry = CatalogEntry;
export type ImageCatalogEntry = CatalogEntry;
export type VideoCatalogEntry = CatalogEntry;

/** Which backend each modality should use for one request; omit to take the backend default. */
export interface ModelSelection {
  modelId?: string;
  imageModelId?: string;
  videoModelId?: string;
}
