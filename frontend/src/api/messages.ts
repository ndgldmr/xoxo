import { apiFetch } from "./client"

export interface BroadcastResponse {
  sent_count: number
  failed_count: number
  total_recipients: number
}

export function broadcastMessage(message: string, level: string | null): Promise<BroadcastResponse> {
  return apiFetch("/broadcast", {
    method: "POST",
    body: JSON.stringify({ message, level }),
  })
}
