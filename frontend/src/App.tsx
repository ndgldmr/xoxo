import { useState } from "react"
import { LoginScreen } from "./components/LoginScreen"
import { StudentsTab } from "./components/StudentsTab"

function hasStoredKey() {
  return Boolean(sessionStorage.getItem("xoxo_api_key"))
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(hasStoredKey)

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

  return <StudentsTab onLogout={handleLogout} />
}
