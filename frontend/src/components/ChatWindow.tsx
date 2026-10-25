import { useEffect, useState } from "react";
import {
  fetchImageModelCatalog,
  fetchModelCatalog,
  fetchVideoModelCatalog,
  streamChatReply,
} from "../api/chatClient";
import { ChatRole, StreamChunkType, type CatalogEntry, type ChatMessage } from "../types/chat";
import { CatalogPicker } from "./CatalogPicker";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

export function ChatWindow(): React.JSX.Element {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [textModels, setTextModels] = useState<CatalogEntry[]>([]);
  const [imageModels, setImageModels] = useState<CatalogEntry[]>([]);
  const [videoModels, setVideoModels] = useState<CatalogEntry[]>([]);

  const [modelId, setModelId] = useState<string | undefined>(undefined);
  const [imageModelId, setImageModelId] = useState<string | undefined>(undefined);
  const [videoModelId, setVideoModelId] = useState<string | undefined>(undefined);

  // A catalog that fails to load leaves its picker empty/disabled rather than
  // breaking the chat — generation still works off the backend's default.
  useEffect(() => {
    fetchModelCatalog()
      .then(setTextModels)
      .catch(() => setTextModels([]));
    fetchImageModelCatalog()
      .then(setImageModels)
      .catch(() => setImageModels([]));
    fetchVideoModelCatalog()
      .then(setVideoModels)
      .catch(() => setVideoModels([]));
  }, []);

  const handleSend = async (text: string): Promise<void> => {
    const conversation: ChatMessage[] = [...messages, { role: ChatRole.User, content: text }];
    setMessages([...conversation, { role: ChatRole.Assistant, content: "" }]);
    setIsStreaming(true);
    setError(null);

    try {
      // Strip the frontend-only `imageUrl`/`videoUrl` display fields before
      // sending — the backend's ChatMessage model doesn't know about them.
      // An image/video-only reply has no token content, but the backend
      // requires non-empty content, so substitute placeholder text for it.
      const wireConversation = conversation.map(({ role, content, imageUrl, videoUrl }) => ({
        role,
        content: content || (imageUrl ? "[Generated image]" : videoUrl ? "[Generated video]" : content),
      }));
      const selection = { modelId, imageModelId, videoModelId };
      for await (const chunk of streamChatReply(wireConversation, selection)) {
        if (chunk.type === StreamChunkType.Token && chunk.content) {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + chunk.content };
            return next;
          });
        } else if (chunk.type === StreamChunkType.Image && chunk.content) {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, imageUrl: chunk.content ?? undefined };
            return next;
          });
        } else if (chunk.type === StreamChunkType.Video && chunk.content) {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, videoUrl: chunk.content ?? undefined };
            return next;
          });
        } else if (chunk.type === StreamChunkType.Error) {
          setError(chunk.content ?? "Something went wrong.");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsStreaming(false);
      // A turn that produced zero tokens and no image/video (a provider error or
      // a safety-guard block) leaves a dead empty bubble — drop it so it
      // doesn't fail the non-empty-content check on a future send.
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === ChatRole.Assistant && !last.content && !last.imageUrl && !last.videoUrl) {
          return prev.slice(0, -1);
        }
        return prev;
      });
    }
  };

  return (
    <div className="chat-window">
      <div className="model-toolbar">
        <CatalogPicker
          label="Chat"
          entries={textModels}
          value={modelId}
          onChange={setModelId}
          emptyHint="none available — check API keys"
        />
        <CatalogPicker
          label="Image"
          entries={imageModels}
          value={imageModelId}
          onChange={setImageModelId}
          emptyHint="none available"
        />
        <CatalogPicker
          label="Video"
          entries={videoModels}
          value={videoModelId}
          onChange={setVideoModelId}
          emptyHint="none available — set COMFYUI_BASE_URL"
        />
      </div>
      <MessageList messages={messages} />
      {error && <div className="chat-error">{error}</div>}
      <MessageInput disabled={isStreaming} onSend={handleSend} />
    </div>
  );
}
