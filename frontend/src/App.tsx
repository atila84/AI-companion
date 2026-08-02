import { ChatWindow } from "./components/ChatWindow";

export function App(): React.JSX.Element {
  return (
    <main className="app">
      <header className="app-header">
        <h1>AI Companion</h1>
        <p className="disclosure">You are chatting with an AI, not a person.</p>
      </header>
      <ChatWindow />
    </main>
  );
}
