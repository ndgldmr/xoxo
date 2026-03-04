import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getSchedule, updateSchedule, type ScheduleConfig } from "@/api/schedule"

const TIMEZONES = [
  "America/Sao_Paulo",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Toronto",
  "Europe/London",
  "Europe/Paris",
  "UTC",
]

export function ScheduleTab() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<ScheduleConfig | null>(null)
  const [saved, setSaved] = useState(false)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["schedule"],
    queryFn: getSchedule,
  })

  // Populate form when data loads
  useEffect(() => {
    if (data) setForm(data)
  }, [data])

  const mutation = useMutation({
    mutationFn: (payload: Partial<ScheduleConfig>) => updateSchedule(payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["schedule"], updated)
      setForm(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form || !data) return
    // Only send fields that changed
    const diff: Partial<ScheduleConfig> = {}
    if (form.theme !== data.theme) diff.theme = form.theme
    if (form.send_time !== data.send_time) diff.send_time = form.send_time
    if (form.timezone !== data.timezone) diff.timezone = form.timezone
    if (Object.keys(diff).length === 0) return
    mutation.mutate(diff)
  }

  function set(field: keyof ScheduleConfig, value: string) {
    setForm((prev) => prev ? { ...prev, [field]: value } : prev)
    setSaved(false)
  }

  const isDirty = data && form && (
    form.theme !== data.theme ||
    form.send_time !== data.send_time ||
    form.timezone !== data.timezone
  )

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading schedule…</p>

  if (isError) {
    const msg = (error as Error).message
    const isUnconfigured = msg.includes("503")
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground max-w-md">
        {isUnconfigured
          ? "Schedule management is not available — GCP Cloud Scheduler environment variables are not configured on the backend."
          : msg}
      </div>
    )
  }

  if (!form) return null

  return (
    <form onSubmit={handleSubmit} className="max-w-md space-y-5">
      <div className="space-y-1.5">
        <Label htmlFor="send_time">Send Time</Label>
        <Input
          id="send_time"
          type="time"
          value={form.send_time}
          onChange={(e) => set("send_time", e.target.value)}
          required
        />
        <p className="text-xs text-muted-foreground">Time the daily message is sent.</p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="timezone">Timezone</Label>
        <Select value={form.timezone} onValueChange={(v) => set("timezone", v)}>
          <SelectTrigger id="timezone">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIMEZONES.map((tz) => (
              <SelectItem key={tz} value={tz}>{tz}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="theme">Theme</Label>
        <Input
          id="theme"
          value={form.theme}
          onChange={(e) => set("theme", e.target.value)}
          placeholder="e.g. daily life, travel, work"
          required
        />
        <p className="text-xs text-muted-foreground">Topic passed to the LLM when generating the daily message.</p>
      </div>

      {mutation.isError && (
        <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
      )}

      <div className="flex items-center gap-3 pt-1">
        <Button type="submit" disabled={!isDirty || mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save changes"}
        </Button>
        {saved && <p className="text-sm text-muted-foreground">Saved.</p>}
        {isDirty && !mutation.isPending && (
          <Button type="button" variant="ghost" size="sm" onClick={() => setForm(data!)}>
            Reset
          </Button>
        )}
      </div>
    </form>
  )
}
