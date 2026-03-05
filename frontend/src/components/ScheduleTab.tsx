import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import ReactMarkdown from "react-markdown"
import { getSchedule, updateSchedule, type ScheduleConfig } from "@/api/schedule"
import { getTodayMessages, generateMessages, type StoredMessage } from "@/api/messages"

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

const LEVELS = ["beginner", "intermediate", "advanced"]

const LEVEL_LABELS: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
}

/** Convert WhatsApp formatting to Markdown before rendering.
 *  WhatsApp: *bold*  _italic_  ~strike~
 *  Markdown:  **bold**  *italic*  ~~strike~~ */
function whatsappToMarkdown(text: string): string {
  return text
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "**$1**") // *bold* → **bold**
    .replace(/(?<!~)~([^~\n]+)~(?!~)/g, "~~$1~~")     // ~strike~ → ~~strike~~
}

function formatGeneratedAt(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function MessageDialog({
  level,
  message,
  open,
  onOpenChange,
  onRegenerate,
  isRegenerating,
  canRegenerate,
}: {
  level: string
  message: StoredMessage | undefined
  open: boolean
  onOpenChange: (open: boolean) => void
  onRegenerate: () => void
  isRegenerating: boolean
  canRegenerate: boolean
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <DialogTitle>{LEVEL_LABELS[level] ?? level}</DialogTitle>
            {message && (
              <span className="text-xs text-muted-foreground font-normal">
                {formatGeneratedAt(message.generated_at)}
              </span>
            )}
          </div>
        </DialogHeader>

        <div className="rounded-md border border-border bg-muted/40 p-4 max-h-96 overflow-y-auto">
          {message ? (
            <div className="prose prose-sm dark:prose-invert max-w-none text-foreground">
              <ReactMarkdown>{whatsappToMarkdown(message.formatted_message)}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              No message generated yet for this level.
            </p>
          )}
        </div>

        {!canRegenerate && !isRegenerating && (
          <p className="text-xs text-muted-foreground">
            Save theme changes before regenerating.
          </p>
        )}

        <DialogFooter showCloseButton>
          <Button
            variant="outline"
            onClick={onRegenerate}
            disabled={!canRegenerate || isRegenerating}
          >
            {isRegenerating ? "Regenerating…" : "Regenerate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function ScheduleTab() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<ScheduleConfig | null>(null)
  const [saved, setSaved] = useState(false)
  const [openLevel, setOpenLevel] = useState<string | null>(null)
  const [regeneratingLevel, setRegeneratingLevel] = useState<string | null>(null)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["schedule"],
    queryFn: getSchedule,
  })

  const { data: todayData, isLoading: todayLoading } = useQuery({
    queryKey: ["messages", "today"],
    queryFn: getTodayMessages,
    enabled: !isError,
  })

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

  const generateMutation = useMutation({
    mutationFn: ({ theme, level }: { theme: string; level?: string }) =>
      generateMessages(theme, level),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages", "today"] })
      setRegeneratingLevel(null)
    },
    onError: () => setRegeneratingLevel(null),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form || !data) return
    const diff: Partial<ScheduleConfig> = {}
    if (form.theme !== data.theme) diff.theme = form.theme
    if (form.send_time !== data.send_time) diff.send_time = form.send_time
    if (form.timezone !== data.timezone) diff.timezone = form.timezone
    if (Object.keys(diff).length === 0) return
    mutation.mutate(diff)
  }

  function set(field: keyof ScheduleConfig, value: string) {
    setForm((prev) => (prev ? { ...prev, [field]: value } : prev))
    setSaved(false)
  }

  function handleRegenerate(level?: string) {
    if (!data) return
    setRegeneratingLevel(level ?? "all")
    generateMutation.mutate({ theme: data.theme, level })
  }

  const isDirty =
    data &&
    form &&
    (form.theme !== data.theme ||
      form.send_time !== data.send_time ||
      form.timezone !== data.timezone)

  const canRegenerate = !isDirty && !generateMutation.isPending

  const messagesByLevel = Object.fromEntries(
    (todayData?.messages ?? []).map((m) => [m.level, m])
  )

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading schedule…</p>

  if (isError) {
    const msg = (error as Error).message
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground max-w-md">
        {msg.includes("503")
          ? "Schedule management is not available — GCP Cloud Scheduler is not configured on the backend."
          : msg}
      </div>
    )
  }

  if (!form) return null

  return (
    <div className="grid grid-cols-2 gap-6 items-start">

      {/* ── Schedule config ── */}
      <section className="rounded-lg border border-border p-5 space-y-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold">Schedule</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                When and what topic to send each day.
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {saved && <span className="text-xs text-muted-foreground">Saved.</span>}
              {isDirty && !mutation.isPending && (
                <Button type="button" variant="ghost" size="sm" onClick={() => setForm(data!)}>
                  Reset
                </Button>
              )}
              <Button size="sm" type="submit" disabled={!isDirty || mutation.isPending}>
                {mutation.isPending ? "Saving…" : "Save changes"}
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="send_time">Send Time</Label>
              <Input
                id="send_time"
                type="time"
                value={form.send_time}
                onChange={(e) => set("send_time", e.target.value)}
                required
              />
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
            <p className="text-xs text-muted-foreground">
              Topic passed to the LLM when generating the daily message.
            </p>
          </div>

          {mutation.isError && (
            <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
          )}
        </form>
      </section>

      {/* ── Today's messages ── */}
      <section className="rounded-lg border border-border p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold">Today's Messages</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Generated at midnight · click a level to preview.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => handleRegenerate()}
            disabled={!canRegenerate || regeneratingLevel === "all"}
            className="flex-shrink-0"
          >
            {regeneratingLevel === "all" ? "Regenerating…" : "Regenerate All"}
          </Button>
        </div>

        {generateMutation.isError && (
          <p className="text-sm text-destructive">
            {(generateMutation.error as Error).message}
          </p>
        )}

        {isDirty && (
          <p className="text-xs text-muted-foreground">
            Save theme changes before regenerating.
          </p>
        )}

        {todayLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="rounded-md border border-border divide-y divide-border">
            {LEVELS.map((level) => {
              const message = messagesByLevel[level]
              const isRegenerating = regeneratingLevel === level
              return (
                <button
                  key={level}
                  type="button"
                  onClick={() => setOpenLevel(level)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/50 transition-colors first:rounded-t-md last:rounded-b-md"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={[
                        "h-2 w-2 rounded-full flex-shrink-0",
                        message ? "bg-green-500" : "bg-muted-foreground/30",
                      ].join(" ")}
                    />
                    <span className="text-sm font-medium">
                      {LEVEL_LABELS[level] ?? level}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    {isRegenerating ? (
                      <span className="text-xs text-muted-foreground">Regenerating…</span>
                    ) : message ? (
                      <span className="text-xs text-muted-foreground">
                        {formatGeneratedAt(message.generated_at)}
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground italic">Not generated</span>
                    )}
                    <Badge variant="outline" className="text-xs">
                      View
                    </Badge>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </section>

      {/* ── Per-level dialog ── */}
      {LEVELS.map((level) => (
        <MessageDialog
          key={level}
          level={level}
          message={messagesByLevel[level]}
          open={openLevel === level}
          onOpenChange={(open) => setOpenLevel(open ? level : null)}
          onRegenerate={() => handleRegenerate(level)}
          isRegenerating={regeneratingLevel === level}
          canRegenerate={canRegenerate}
        />
      ))}
    </div>
  )
}
