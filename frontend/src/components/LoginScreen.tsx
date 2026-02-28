import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { apiFetch } from "@/api/client"

interface Props {
  onLogin: () => void
}

export function LoginScreen({ onLogin }: Props) {
  const [key, setKey] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    sessionStorage.setItem("xoxo_api_key", key)
    try {
      // Verify by hitting a lightweight authenticated endpoint
      await apiFetch("/students?include_inactive=false")
      onLogin()
    } catch (err) {
      sessionStorage.removeItem("xoxo_api_key")
      setError(err instanceof Error ? err.message : "Invalid API key")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-card p-8 shadow-sm"
      >
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">XOXO Admin</h1>
          <p className="text-sm text-muted-foreground">Enter your API key to continue.</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="apikey">API Key</Label>
          <Input
            id="apikey"
            type="password"
            placeholder="••••••••••••••••"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            required
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Verifying…" : "Sign in"}
        </Button>
      </form>
    </div>
  )
}
