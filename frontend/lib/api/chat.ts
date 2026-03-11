import type { ChatRequest } from "../types/chat";
import { apiClient } from "./client";

export async function sendChatMessage(request: ChatRequest): Promise<Response> {
  return fetch(`${apiClient.defaults.baseURL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}
