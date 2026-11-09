import type { components } from "./api-types.gen"

export type ChatResponse = components["schemas"]["ChatResponse"]
export type Emotion = components["schemas"]["Emotion"]
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

export interface SendChatInput {
  sessionId: string
  message: string
  goal?: string | null
  signal?: AbortSignal
}

export async function sendChat({
  sessionId,
  message,
  goal,
  signal,
}: SendChatInput): Promise<ChatResponse> {
  const form = new FormData()
  form.append("session_id", sessionId)
  form.append("message", message)
  if (goal) form.append("goal", goal)
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    body: form,
    signal,
  })
  if (!res.ok) throw await toApiError(res)
  return (await res.json()) as ChatResponse
}

export const getMeta = (signal?: AbortSignal) =>
  getJson<MetaResponse>("/meta", signal)

export const getHealth = (signal?: AbortSignal) =>
  getJson<HealthResponse>("/health", signal)

export const getSession = (sessionId: string, signal?: AbortSignal) =>
  getJson<SessionResponse>(`/session/${encodeURIComponent(sessionId)}`, signal)
