import type { components } from "./api-types.gen"

export type ChatResponse = components["schemas"]["ChatResponse"]
export type Emotion = components["schemas"]["Emotion"]
export type Analysis = components["schemas"]["Analysis"]
export type Song = components["schemas"]["Song"]
export type ResponseMeta = components["schemas"]["Meta"]
export type SessionResponse = components["schemas"]["SessionResponse"]
export type SessionTurn = components["schemas"]["SessionTurn"]
export type MetaResponse = components["schemas"]["MetaResponse"]
export type HealthResponse = components["schemas"]["HealthResponse"]

export const API_BASE = "/api"

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail = res.statusText
  try {
    const body = await res.json()
    if (typeof body?.detail === "string") detail = body.detail
    else if (Array.isArray(body?.detail))
      detail = body.detail.map((d: { msg?: string }) => d.msg).join("; ")
  } catch {
    /* thân phản hồi không phải JSON */
  }
  return new ApiError(res.status, detail)
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { signal })
  if (!res.ok) throw await toApiError(res)
  return (await res.json()) as T
}

export interface SendChatAudio {
  blob: Blob
  filename: string
}

export interface SendChatInput {
  sessionId: string
  /** Bỏ trống khi gửi tin giọng nói. */
  message?: string
  goal?: string | null
  audio?: SendChatAudio
  /** Chữ nhận dạng sẵn trên trình duyệt (Web Speech), dùng khi server nhận dạng lỗi. */
  transcriptHint?: string
  signal?: AbortSignal
}

export async function sendChat({
  sessionId,
  message,
  goal,
  audio,
  transcriptHint,
  signal,
}: SendChatInput): Promise<ChatResponse> {
  const form = new FormData()
  form.append("session_id", sessionId)
  if (message) form.append("message", message)
  if (goal) form.append("goal", goal)
  if (audio) form.append("audio_file", audio.blob, audio.filename)
  if (transcriptHint?.trim())
    form.append("transcript_hint", transcriptHint.trim())
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    body: form,
    signal,
  })
  if (!res.ok) throw await toApiError(res)
  return (await res.json()) as ChatResponse
}

export type Rating = "up" | "down"

export async function sendFeedback(
  sessionId: string,
  turnId: string,
  rating: Rating,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      turn_id: turnId,
      rating,
    }),
    signal,
  })
  if (!res.ok) throw await toApiError(res)
}

/** Xoá phiên trên server (204 kể cả khi phiên không tồn tại). */
export async function deleteSession(
  sessionId: string,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/session/${encodeURIComponent(sessionId)}`,
    { method: "DELETE", signal }
  )
  if (!res.ok) throw await toApiError(res)
}

export const getMeta = (signal?: AbortSignal) =>
  getJson<MetaResponse>("/meta", signal)

export const getHealth = (signal?: AbortSignal) =>
  getJson<HealthResponse>("/health", signal)

export const getSession = (sessionId: string, signal?: AbortSignal) =>
  getJson<SessionResponse>(`/session/${encodeURIComponent(sessionId)}`, signal)
