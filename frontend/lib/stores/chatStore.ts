import { create } from "zustand";
import type { Message } from "../types/chat";

type ChatState = {
  messages: Message[];
  isStreaming: boolean;
  addMessage: (message: Message) => void;
  appendToLastMessage: (chunk: string) => void;
  setStreaming: (value: boolean) => void;
  clear: () => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  appendToLastMessage: (chunk) =>
    set((state) => {
      if (state.messages.length === 0) return state;
      const messages = [...state.messages];
      messages[messages.length - 1] = {
        ...messages[messages.length - 1],
        content: messages[messages.length - 1].content + chunk,
      };
      return { messages };
    }),
  setStreaming: (value) => set({ isStreaming: value }),
  clear: () => set({ messages: [], isStreaming: false }),
}));
