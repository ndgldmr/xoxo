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

export interface StoredMessage {
  level: string
  theme: string
  formatted_message: string
  generated_at: string  // ISO datetime
}

export interface TodayMessagesResponse {
  date: string
  messages: StoredMessage[]
}

export interface GeneratedMessage {
  level: string
  theme: string
  formatted_message: string | null
  valid: boolean
  validation_errors: string[]
}

export interface GenerateResponse {
  date: string
  results: GeneratedMessage[]
}

export function getTodayMessages(): Promise<TodayMessagesResponse> {
  return apiFetch("/messages/today")
}

export function generateMessages(theme: string, level?: string): Promise<GenerateResponse> {
  return apiFetch("/messages/generate", {
    method: "POST",
    body: JSON.stringify({ theme, level: level ?? null }),
  })
}
