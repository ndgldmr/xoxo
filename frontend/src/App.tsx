import { useState } from "react"
import { LoginScreen } from "./components/LoginScreen"
import { StudentsTab } from "./components/StudentsTab"
import { ScheduleTab } from "./components/ScheduleTab"
import { Button } from "@/components/ui/button"

type Tab = "students" | "schedule"

const TABS: { id: Tab; label: string }[] = [
  { id: "students", label: "Students" },
  { id: "schedule", label: "Schedule" },
]

function hasStoredKey() {
  return Boolean(sessionStorage.getItem("xoxo_api_key"))
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(hasStoredKey)
  const [activeTab, setActiveTab] = useState<Tab>("students")

  function handleLogin() {
    setLoggedIn(true)
  }

  function handleLogout() {
    sessionStorage.removeItem("xoxo_api_key")
    setLoggedIn(false)
  }

  if (!loggedIn) {
    return <LoginScreen onLogin={handleLogin} />
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          <span className="font-semibold">XOXO Admin</span>
          <nav className="flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={[
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  activeTab === tab.id
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                ].join(" ")}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <div className="ml-auto">
            <Button variant="outline" size="sm" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-6xl px-6 py-6">
        {activeTab === "students" && <StudentsTab />}
        {activeTab === "schedule" && <ScheduleTab />}
      </main>
    </div>
  )
}
