import { useCallback, useEffect, useReducer, useRef, useState } from "react"
import { ApiError, getSession, sendChat } from "@/lib/api"
import type { ResponseMeta } from "@/lib/api"
import { messagesKey, readJson, writeJson } from "@/lib/storage"
import {
  chatReducer,
  initialState,
  toStored,
  turnsToMessages,
  type ChatMessage,
} from "./chat-state"

function newId(): string {
  try {
    return crypto.randomUUID()
  } catch {
    return `m-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
  }
}

function loadLocal(sessionId: string): ChatMessage[] {
  const stored = readJson<ChatMessage[]>(messagesKey(sessionId))
  return Array.isArray(stored) ? stored : []
}

export function errorText(err: unknown): string {
  if (err instanceof ApiError) return err.detail || `Lỗi ${err.status}`
  return "Không kết nối được tới máy chủ."
}

export function useChat(sessionId: string, goal: string | null) {
  const [state, dispatch] = useReducer(chatReducer, undefined, () =>
    initialState(sessionId, loadLocal(sessionId))
  )
  const [lastMeta, setLastMeta] = useState<ResponseMeta | null>(null)
  const sessionRef = useRef(sessionId)
  const messagesRef = useRef(state.messages)
  useEffect(() => {
    sessionRef.current = sessionId
    messagesRef.current = state.messages
  })

  // Đổi phiên hoặc mount: nạp từ localStorage, nếu trống thì khôi phục từ backend.
  useEffect(() => {
    const local = loadLocal(sessionId)
    dispatch({ type: "switch", sessionId, messages: local })
    if (local.length > 0) return
    const controller = new AbortController()
    getSession(sessionId, controller.signal)
      .then((res) => {
        if (res.turns.length > 0) {
          dispatch({ type: "hydrate", sessionId, messages: turnsToMessages(res.turns) })
        }
      })
      .catch(() => {
        /* backend chưa chạy hoặc phiên chưa có: bắt đầu trống */
      })
    return () => controller.abort()
  }, [sessionId])

  // Lưu tin đã hoàn tất.
  useEffect(() => {
    if (state.sessionId !== sessionId) return
    writeJson(messagesKey(sessionId), toStored(state.messages))
  }, [state, sessionId])

  const deliver = useCallback(
    async (userId: string, text: string, msgGoal: string | null) => {
      const forSession = sessionRef.current
      try {
        const response = await sendChat({ sessionId: forSession, message: text, goal: msgGoal })
        if (sessionRef.current !== forSession) return
        setLastMeta(response.meta)
        dispatch({
          type: "resolve",
          userId,
          botId: newId(),
          response,
          createdAt: new Date().toISOString(),
        })
      } catch (err) {
        if (sessionRef.current !== forSession) return
        dispatch({ type: "fail", userId, error: errorText(err) })
      }
    },
    []
  )

  const pending = state.messages.some((m) => m.role === "user" && m.status === "sending")

  const send = useCallback(
    (raw: string): boolean => {
      const text = raw.trim()
      if (!text) return false
      if (messagesRef.current.some((m) => m.role === "user" && m.status === "sending")) return false
      const id = newId()
      dispatch({ type: "send", id, text, goal, createdAt: new Date().toISOString() })
      void deliver(id, text, goal)
      return true
    },
    [deliver, goal]
  )

  const retry = useCallback(
    (userId: string) => {
      const msg = messagesRef.current.find((m) => m.id === userId)
      if (!msg || msg.role !== "user" || msg.status !== "error") return
      dispatch({ type: "retry", userId })
      void deliver(userId, msg.text, msg.goal)
    },
    [deliver]
  )

  const resetMeta = useCallback(() => setLastMeta(null), [])

  return {
    messages: state.sessionId === sessionId ? state.messages : [],
    pending,
    lastMeta,
    send,
    retry,
    resetMeta,
  }
}
