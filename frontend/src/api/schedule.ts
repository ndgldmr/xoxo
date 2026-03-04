import { apiFetch } from "./client"

export interface ScheduleConfig {
  theme: string
  send_time: string   // "HH:MM"
  timezone: string    // IANA timezone string
}

export function getSchedule(): Promise<ScheduleConfig> {
  return apiFetch("/schedule")
}

export function updateSchedule(payload: Partial<ScheduleConfig>): Promise<ScheduleConfig> {
  return apiFetch("/schedule", {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}
