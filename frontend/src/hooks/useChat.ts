import { useCallback, useEffect, useReducer, useRef, useState } from "react"
import { ApiError, getSession, sendChat, sendFeedback } from "@/lib/api"
import type { Rating, ResponseMeta } from "@/lib/api"
import { messagesKey, readJson, writeJson } from "@/lib/storage"
import { filenameFor } from "./useRecorder"
import type { VoiceRecording } from "./useVoiceRecording"
import {
  audioUrlsOf,
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

/** Dữ liệu cần giữ để gửi lại tin giọng nói khi lỗi (không đưa vào state/localStorage). */
interface VoicePayload {
  blob: Blob
  filename: string
  transcriptHint: string
}

export function useChat(sessionId: string, goal: string | null) {
  const [state, dispatch] = useReducer(chatReducer, undefined, () =>
    initialState(sessionId, loadLocal(sessionId))
  )
  const [lastMeta, setLastMeta] = useState<ResponseMeta | null>(null)
  const sessionRef = useRef(sessionId)
  const messagesRef = useRef(state.messages)
  const voiceRef = useRef(new Map<string, VoicePayload>())
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
          dispatch({
            type: "hydrate",
            sessionId,
            messages: turnsToMessages(res.turns),
          })
        }
      })
      .catch(() => {
        /* backend chưa chạy hoặc phiên chưa có: bắt đầu trống */
      })
    return () => controller.abort()
  }, [sessionId])

  // Đổi/đặt lại phiên hoặc rời trang: thu hồi object URL của các bản ghi cũ.
  useEffect(
    () => () => {
      audioUrlsOf(messagesRef.current).forEach((url) =>
        URL.revokeObjectURL(url)
      )
      voiceRef.current.clear()
    },
    [sessionId]
  )

  // Lưu tin đã hoàn tất.
  useEffect(() => {
    if (state.sessionId !== sessionId) return
    writeJson(messagesKey(sessionId), toStored(state.messages))
  }, [state, sessionId])

  const deliver = useCallback(
    async (userId: string, text: string, msgGoal: string | null) => {
      const forSession = sessionRef.current
      const voice = voiceRef.current.get(userId)
      try {
        const response = await sendChat(
          voice
            ? {
                sessionId: forSession,
                goal: msgGoal,
                audio: { blob: voice.blob, filename: voice.filename },
                transcriptHint: voice.transcriptHint,
              }
            : { sessionId: forSession, message: text, goal: msgGoal }
        )
        if (sessionRef.current !== forSession) return
        setLastMeta(response.meta)
        voiceRef.current.delete(userId)
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

  const pending = state.messages.some(
    (m) => m.role === "user" && m.status === "sending"
  )

  const send = useCallback(
    (raw: string): boolean => {
      const text = raw.trim()
      if (!text) return false
      if (
        messagesRef.current.some(
          (m) => m.role === "user" && m.status === "sending"
        )
      )
        return false
      const id = newId()
      dispatch({
        type: "send",
        id,
        text,
        goal,
        createdAt: new Date().toISOString(),
      })
      void deliver(id, text, goal)
      return true
    },
    [deliver, goal]
  )

  const sendVoice = useCallback(
    (voice: VoiceRecording): boolean => {
      if (
        messagesRef.current.some(
          (m) => m.role === "user" && m.status === "sending"
        )
      )
        return false
      const id = newId()
      const audioUrl = URL.createObjectURL(voice.blob)
      voiceRef.current.set(id, {
        blob: voice.blob,
        filename: filenameFor(voice.mimeType),
        transcriptHint: voice.transcriptHint,
      })
      dispatch({
        type: "send",
        id,
        text: voice.transcriptHint.trim(),
        goal,
        createdAt: new Date().toISOString(),
        voice: { audioUrl, durationMs: voice.durationMs },
      })
      void deliver(id, voice.transcriptHint, goal)
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

  /** Gửi đánh giá: cập nhật ngay (optimistic), hoàn tác và trả false nếu lỗi. */
  const rate = useCallback(
    async (botId: string, rating: Rating): Promise<boolean> => {
      const msg = messagesRef.current.find((m) => m.id === botId)
      if (!msg || msg.role !== "bot" || !msg.turnId) return false
      if (msg.rating === rating) return true
      const previous = msg.rating ?? null
      const forSession = sessionRef.current
      dispatch({ type: "rate", botId, rating })
      try {
        await sendFeedback(forSession, msg.turnId, rating)
        return true
      } catch {
        if (sessionRef.current === forSession)
          dispatch({ type: "rate", botId, rating: previous })
        return false
      }
    },
    []
  )

  const resetMeta = useCallback(() => setLastMeta(null), [])

  return {
    messages: state.sessionId === sessionId ? state.messages : [],
    pending,
    lastMeta,
    send,
    sendVoice,
    retry,
    rate,
    resetMeta,
  }
}
