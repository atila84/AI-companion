import { useState } from "react";
import { streamChatReply } from "../api/chatClient";
import { ChatRole, StreamChunkType, type ChatMessage } from "../types/chat";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import { ModelPicker } from "./ModelPicker";

export function ChatWindow(): React.JSX.Element {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelId, setModelId] = useState<string | undefined>(undefined);

  const handleSend = async (text: string): Promise<void> => {
    const conversation: ChatMessage[] = [...messages, { role: ChatRole.User, content: text }];
    setMessages([...conversation, { role: ChatRole.Assistant, content: "" }]);
    setIsStreaming(true);
    setError(null);

    try {
      // Strip the frontend-only `imageUrl` display field before sending —
      // the backend's ChatMessage model doesn't know about it.
      const wireConversation = conversation.map(({ role, content }) => ({ role, content }));
      for await (const chunk of streamChatReply(wireConversation, modelId)) {
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
        } else if (chunk.type === StreamChunkType.Error) {
          setError(chunk.content ?? "Something went wrong.");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="chat-window">
      <ModelPicker value={modelId} onChange={setModelId} />
      <MessageList messages={messages} />
      {error && <div className="chat-error">{error}</div>}
      <MessageInput disabled={isStreaming} onSend={handleSend} />
    </div>
  );
}
