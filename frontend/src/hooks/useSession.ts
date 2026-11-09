import { useCallback, useState } from "react"
import { SESSION_KEY, messagesKey, readItem, removeItem, writeItem } from "@/lib/storage"

function newId(): string {
  try {
    return crypto.randomUUID()
  } catch {
    return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
  }
}

function loadOrCreate(): string {
  const existing = readItem(SESSION_KEY)
  if (existing) return existing
  const id = newId()
  writeItem(SESSION_KEY, id)
  return id
}

export function useSession() {
  const [sessionId, setSessionId] = useState(loadOrCreate)

  /** Tạo session_id mới, xoá tin đã lưu của phiên cũ. */
  const newSession = useCallback(() => {
    const id = newId()
    setSessionId((old) => {
      removeItem(messagesKey(old))
      return id
    })
    writeItem(SESSION_KEY, id)
    return id
  }, [])

  return { sessionId, newSession }
}
