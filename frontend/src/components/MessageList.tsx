import { useEffect, useRef } from "react";
import { ChatRole, type ChatMessage } from "../types/chat";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps): React.JSX.Element {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`message message--${message.role === ChatRole.User ? "user" : "assistant"}`}
        >
          {message.content}
          {message.imageUrl && (
            <img src={message.imageUrl} alt={message.content || "Generated image"} className="message-image" />
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
