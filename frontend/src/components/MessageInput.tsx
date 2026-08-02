import { useState } from "react";
import type { KeyboardEvent } from "react";

interface MessageInputProps {
  disabled: boolean;
  onSend: (text: string) => void;
}

export function MessageInput({ disabled, onSend }: MessageInputProps): React.JSX.Element {
  const [text, setText] = useState("");

  const handleSend = (): void => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="message-input">
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Message your companion..."
        disabled={disabled}
        rows={2}
      />
      <button onClick={handleSend} disabled={disabled || !text.trim()}>
        Send
      </button>
    </div>
  );
}
