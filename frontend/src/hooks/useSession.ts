import { useCallback, useState } from "react"
import {
  CONVERSATIONS_KEY,
  SESSION_KEY,
  messagesKey,
  readItem,
  readJson,
  removeItem,
  writeItem,
  writeJson,
} from "@/lib/storage"

/** Một mục trong danh sách lịch sử ở sidebar (chỉ lưu trên trình duyệt này). */
export interface Conversation {
  id: string
  title: string
  /** ISO time của tin gần nhất. */
  updatedAt: string
}

/** Giữ tối đa chừng này cuộc; cuộc cũ hơn bị xoá cả tin nhắn. */
export const MAX_CONVERSATIONS = 50

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

function isConversation(v: unknown): v is Conversation {
  if (typeof v !== "object" || v === null) return false
  const c = v as Record<string, unknown>
  return (
    typeof c.id === "string" &&
    typeof c.title === "string" &&
    typeof c.updatedAt === "string"
  )
}

function loadConversations(): Conversation[] {
  const raw = readJson<unknown>(CONVERSATIONS_KEY)
  return Array.isArray(raw) ? raw.filter(isConversation) : []
}

function sortByRecent(list: Conversation[]): Conversation[] {
  return [...list].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

export function useSession() {
  const [sessionId, setSessionId] = useState(loadOrCreate)
  const [conversations, setConversations] = useState(loadConversations)

  const save = useCallback((next: Conversation[]) => {
    writeJson(CONVERSATIONS_KEY, next)
    return next
  }, [])

  const switchTo = useCallback((id: string) => {
    setSessionId(id)
    writeItem(SESSION_KEY, id)
  }, [])

  /** Bắt đầu cuộc mới; cuộc cũ vẫn nằm trong lịch sử. */
  const newSession = useCallback(() => {
    const id = newId()
    switchTo(id)
    return id
  }, [switchTo])

  const selectSession = useCallback(
    (id: string) => {
      switchTo(id)
    },
    [switchTo]
  )

  /** Ghi/cập nhật tiêu đề và thời gian của một cuộc (gọi khi có tin mới). */
  const recordConversation = useCallback(
    (entry: Conversation) => {
      setConversations((list) => {
        const old = list.find((c) => c.id === entry.id)
        if (
          old &&
          old.title === entry.title &&
          old.updatedAt === entry.updatedAt
        ) {
          return list
        }
        const merged = sortByRecent([
          entry,
          ...list.filter((c) => c.id !== entry.id),
        ])
        merged
          .slice(MAX_CONVERSATIONS)
          .forEach((c) => removeItem(messagesKey(c.id)))
        return save(merged.slice(0, MAX_CONVERSATIONS))
      })
    },
    [save]
  )

  /** Xoá hẳn một cuộc khỏi trình duyệt; xoá cuộc đang mở thì chuyển sang cuộc mới. */
  const deleteConversation = useCallback(
    (id: string) => {
      removeItem(messagesKey(id))
      setConversations((list) => save(list.filter((c) => c.id !== id)))
      setSessionId((current) => {
        if (current !== id) return current
        const fresh = newId()
        writeItem(SESSION_KEY, fresh)
        return fresh
      })
    },
    [save]
  )

  return {
    sessionId,
    newSession,
    conversations,
    selectSession,
    recordConversation,
    deleteConversation,
  }
}
