import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { broadcastMessage } from "@/api/messages"

const LEVEL_OPTIONS = [
  { value: "all", label: "All levels" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
]

export function AnnouncementTab() {
  const [message, setMessage] = useState("")
  const [level, setLevel] = useState("all")
  const [result, setResult] = useState<{ sent: number; failed: number } | null>(null)

  const mutation = useMutation({
    mutationFn: () => broadcastMessage(message, level === "all" ? null : level),
    onSuccess: (data) => {
      setResult({ sent: data.sent_count, failed: data.failed_count })
      setMessage("")
      setTimeout(() => setResult(null), 5000)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!message.trim()) return
    setResult(null)
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-lg space-y-5">
      <div className="space-y-1.5">
        <Label htmlFor="level">Recipients</Label>
        <Select value={level} onValueChange={setLevel}>
          <SelectTrigger id="level">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LEVEL_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Only active students who have opted in to WhatsApp messages will receive this.
        </p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="message">Message</Label>
        <Textarea
          id="message"
          rows={6}
          placeholder="Type your announcement here…"
          value={message}
          onChange={(e) => {
            setMessage(e.target.value)
            setResult(null)
          }}
          required
        />
      </div>

      {mutation.isError && (
        <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
      )}

      {result && (
        <p className="text-sm text-muted-foreground">
          Sent to {result.sent} student{result.sent !== 1 ? "s" : ""}
          {result.failed > 0 ? ` (${result.failed} failed)` : "."
          }
        </p>
      )}

      <Button type="submit" disabled={!message.trim() || mutation.isPending}>
        {mutation.isPending ? "Sending…" : "Send announcement"}
      </Button>
    </form>
  )
}
