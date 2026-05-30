import { create } from "zustand";
import type { ChatMessage, SessionData } from "@/app/types";

type Store = {
  session: SessionData | null;
  messages: ChatMessage[];
  isIngesting: boolean;
  isChatLoading: boolean;
  error: string | null;
  setSession: (s: SessionData) => void;
  addMessage: (m: ChatMessage) => void;
  updateLastMessage: (content: string, citations?: any[]) => void;
  setIsIngesting: (v: boolean) => void;
  setIsChatLoading: (v: boolean) => void;
  setError: (e: string | null) => void;
  clearMessages: () => void;
};

export const useStore = create<Store>((set) => ({
  session: null,
  messages: [],
  isIngesting: false,
  isChatLoading: false,
  error: null,

  setSession: (session) => set({ session }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateLastMessage: (content, citations) =>
    set((state) => {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last && last.role === "assistant") {
        messages[messages.length - 1] = {
          ...last,
          content,
          citations: citations ?? last.citations,
          isStreaming: false,
        };
      }
      return { messages };
    }),

  setIsIngesting: (isIngesting) => set({ isIngesting }),
  setIsChatLoading: (isChatLoading) => set({ isChatLoading }),
  setError: (error) => set({ error }),
  clearMessages: () => set({ messages: [] }),
}));
