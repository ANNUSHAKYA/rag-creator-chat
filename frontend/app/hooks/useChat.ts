import { useStore } from "@/app/store/useStore";
import type { Citation } from "@/app/types";

const API = process.env.NEXT_PUBLIC_API_URL;

export function useChat() {
  const {
    session,
    addMessage,
    updateLastMessage,
    setIsChatLoading,
    setError,
  } = useStore();

  const sendMessage = async (question: string) => {
    if (!session || !question.trim()) return;

    // Add user message immediately
    addMessage({
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    });

    // Add empty assistant placeholder — filled by streaming
    addMessage({
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      isStreaming: true,
    });

    setIsChatLoading(true);
    setError(null);

    let accumulated = "";
    let citations: Citation[] = [];

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: session.session_id,
          question,
        }),
      });

      if (!response.ok) throw new Error("Chat request failed");
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // Manual SSE line parser — avoids eventsource-parser edge cases
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep the last incomplete line in buffer
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);

          if (data === "[DONE]") break;

          if (data.startsWith("[CITATIONS]")) {
            try {
              citations = JSON.parse(data.slice(11));
            } catch {}
            continue;
          }

          accumulated += data;
          // Re-render on every token
          updateLastMessage(accumulated);
        }
      }

      // Final flush — attach citations
      updateLastMessage(accumulated, citations);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
      updateLastMessage("Sorry, something went wrong. Please try again.");
    } finally {
      setIsChatLoading(false);
    }
  };

  return { sendMessage };
}
