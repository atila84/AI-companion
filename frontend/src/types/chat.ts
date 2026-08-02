// Mirrors of backend Pydantic models in backend/src/models/chat.py.
// Keep these two in sync by hand for now — no shared schema/codegen in this increment.

export enum ChatRole {
  User = "user",
  Assistant = "assistant",
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
}

export enum StreamChunkType {
  Token = "token",
  Done = "done",
  Error = "error",
}

export interface StreamChunk {
  type: StreamChunkType;
  content: string | null;
}
