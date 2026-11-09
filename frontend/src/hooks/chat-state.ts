import type { ChatResponse, Emotion, SessionTurn, Song } from "@/lib/api"

export type MessageStatus = "sending" | "sent" | "error"

export interface UserMessage {
  id: string
  role: "user"
  text: string
  status: MessageStatus
  createdAt: string
  goal: string | null
  /** Cảm xúc của lượt này (null khi chưa có hoặc lượt an toàn). */
  emotion: Emotion | null
  error?: string
  /** Tin giọng nói: `text` là transcript (chữ dự phòng khi chờ, chữ của server khi đã có). */
  kind?: "voice"
  /** Object URL của bản ghi tại máy; không lưu vào localStorage. */
  audioUrl?: string
  durationMs?: number
}

export interface BotMessage {
  id: string
  role: "bot"
  text: string
  status: "sent"
  createdAt: string
  songs: Song[]
  safety: boolean
  replyTo: string
  /** Chỉ true với tin vừa nhận (để hiện dần); không lưu vào localStorage. */
  fresh?: boolean
}

export type ChatMessage = UserMessage | BotMessage

export interface ChatState {
  sessionId: string
  messages: ChatMessage[]
}

export type ChatAction =
  | {
      type: "send"
      id: string
      text: string
      goal: string | null
      createdAt: string
      voice?: { audioUrl: string; durationMs: number }
    }
  | {
      type: "resolve"
      userId: string
      botId: string
      response: ChatResponse
      createdAt: string
    }
  | { type: "fail"; userId: string; error: string }
  | { type: "retry"; userId: string }
  | { type: "switch"; sessionId: string; messages: ChatMessage[] }
  | { type: "hydrate"; sessionId: string; messages: ChatMessage[] }

export const MAX_STORED_MESSAGES = 100

export function initialState(
  sessionId: string,
  messages: ChatMessage[]
): ChatState {
  return { sessionId, messages }
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "send":
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: action.id,
            role: "user",
            text: action.text,
            status: "sending",
            createdAt: action.createdAt,
            goal: action.goal,
            emotion: null,
            ...(action.voice
              ? {
                  kind: "voice" as const,
                  audioUrl: action.voice.audioUrl,
                  durationMs: action.voice.durationMs,
                }
              : {}),
          },
        ],
      }
    case "resolve": {
      const { response } = action
      const messages = state.messages.map((m): ChatMessage =>
        m.id === action.userId && m.role === "user"
          ? {
              ...m,
              status: "sent",
              error: undefined,
              emotion: response.safety ? null : (response.emotion ?? null),
              text:
                m.kind === "voice"
                  ? response.transcript?.trim() || m.text
                  : m.text,
            }
          : m
      )
      messages.push({
        id: action.botId,
        role: "bot",
        text: response.reply,
        status: "sent",
        createdAt: action.createdAt,
        songs: response.safety ? [] : (response.songs ?? []),
        safety: response.safety ?? false,
        replyTo: action.userId,
        fresh: true,
      })
      return { ...state, messages }
    }
    case "fail":
      return {
        ...state,
        messages: state.messages.map((m): ChatMessage =>
          m.id === action.userId && m.role === "user"
            ? { ...m, status: "error", error: action.error }
            : m
        ),
      }
    case "retry":
      return {
        ...state,
        messages: state.messages.map((m): ChatMessage =>
          m.id === action.userId && m.role === "user"
            ? { ...m, status: "sending", error: undefined }
            : m
        ),
      }
    case "switch":
      return { sessionId: action.sessionId, messages: action.messages }
    case "hydrate":
      // Bỏ qua nếu đã đổi phiên hoặc người dùng đã kịp gửi tin.
      if (state.sessionId !== action.sessionId || state.messages.length > 0)
        return state
      return { ...state, messages: action.messages }
  }
}

/** Chỉ lưu tin đã hoàn tất, tối đa 100 tin gần nhất, bỏ cờ `fresh`. */
export function toStored(messages: ChatMessage[]): ChatMessage[] {
  return messages
    .filter((m) => m.role === "bot" || m.status === "sent")
    .slice(-MAX_STORED_MESSAGES)
    .map((m) => {
      if (m.role === "bot") {
        const { fresh: _fresh, ...rest } = m
        void _fresh
        return rest
      }
      if (m.kind === "voice") {
        const { audioUrl: _audioUrl, ...rest } = m
        void _audioUrl
        return rest
      }
      return m
    })
}

/** Các object URL của bản ghi, để thu hồi khi đổi/xoá phiên. */
export function audioUrlsOf(messages: ChatMessage[]): string[] {
  return messages.flatMap((m) =>
    m.role === "user" && m.audioUrl ? [m.audioUrl] : []
  )
}

/** Chuyển các lượt từ GET /api/session/{id} thành danh sách tin. */
export function turnsToMessages(turns: SessionTurn[]): ChatMessage[] {
  return turns.flatMap((t): ChatMessage[] => {
    const userId = `${t.turn_id}-u`
    return [
      {
        id: userId,
        role: "user",
        text: t.transcript || t.user_text || "",
        status: "sent",
        createdAt: t.created_at,
        goal: null,
        emotion: t.safety ? null : (t.emotion ?? null),
        ...(t.transcript ? { kind: "voice" as const } : {}),
      },
      {
        id: `${t.turn_id}-b`,
        role: "bot",
        text: t.reply,
        status: "sent",
        createdAt: t.created_at,
        songs: t.safety ? [] : (t.songs ?? []),
        safety: t.safety ?? false,
        replyTo: userId,
      },
    ]
  })
}
