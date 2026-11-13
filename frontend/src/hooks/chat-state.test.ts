import { describe, expect, it } from "vitest"
import type { ChatResponse, SessionTurn } from "@/lib/api"
import {
  MAX_STORED_MESSAGES,
  chatReducer,
  initialState,
  toStored,
  turnsToMessages,
  type ChatMessage,
  type ChatState,
} from "./chat-state"

const response: ChatResponse = {
  turn_id: "t1",
  reply: "Mình nghe đây.",
  emotion: {
    label: "Sadness",
    probs: { Sadness: 0.62, Other: 0.2 },
    arousal: "low",
  },
  songs: [{ title: "A", artist: "B", youtube_url: "https://youtu.be/abc123", reason: "r" }],
  safety: false,
  meta: {
    llm_backend: "mock",
    model_mode: "mock",
    modules: {},
    degraded: false,
    latency_ms: 1,
    warnings: [],
    music_decision: "chip",
    fusion_applied: false,
  },
}

const sent = (s: ChatState) =>
  chatReducer(s, { type: "send", id: "u1", text: "hôm nay buồn", goal: "xoa_diu", createdAt: "now" })

describe("chatReducer", () => {
  it("send thêm tin người dùng ở trạng thái sending", () => {
    const s = sent(initialState("s", []))
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0]).toMatchObject({ role: "user", status: "sending", goal: "xoa_diu" })
  })

  it("resolve chuyển sang sent, gắn cảm xúc và thêm tin bot", () => {
    let s = sent(initialState("s", []))
    s = chatReducer(s, { type: "resolve", userId: "u1", botId: "b1", response, createdAt: "now" })
    expect(s.messages).toHaveLength(2)
    expect(s.messages[0]).toMatchObject({ status: "sent", emotion: { label: "Sadness" } })
    expect(s.messages[1]).toMatchObject({ role: "bot", text: "Mình nghe đây.", fresh: true })
  })

  it("resolve lưu analysis, emotion, latency vào tin bot", () => {
    const analysis = {
      turn: 2,
      recent_emotions: [{ turn: 1, label: "Fear" }],
      last_music_turn: null,
      tone: { key: "sad", text: "Chậm, dịu." },
      music_reason: "Chưa cần gợi ý nhạc ở lượt này",
      emotion_source: "module" as const,
    }
    let s = sent(initialState("s", []))
    s = chatReducer(s, {
      type: "resolve",
      userId: "u1",
      botId: "b1",
      response: {
        ...response,
        meta: { ...response.meta, latency_ms: 1234, analysis },
      },
      createdAt: "now",
    })
    expect(s.messages[1]).toMatchObject({
      analysis,
      emotion: { label: "Sadness" },
      latencyMs: 1234,
    })
  })

  it("response không có analysis: tin bot không có khung", () => {
    let s = sent(initialState("s", []))
    s = chatReducer(s, { type: "resolve", userId: "u1", botId: "b1", response, createdAt: "now" })
    expect(s.messages[1]).toMatchObject({ analysis: null })
  })

  it("analysis và emotion của tin bot sống sót qua toStored (localStorage)", () => {
    const analysis = {
      turn: 1,
      recent_emotions: [],
      last_music_turn: null,
      tone: null,
      music_reason: "Không gợi ý nhạc ở lượt cần hỗ trợ an toàn",
      emotion_source: null,
    }
    let s = sent(initialState("s", []))
    s = chatReducer(s, {
      type: "resolve",
      userId: "u1",
      botId: "b1",
      response: { ...response, meta: { ...response.meta, analysis } },
      createdAt: "now",
    })
    const round = JSON.parse(JSON.stringify(toStored(s.messages))) as ChatMessage[]
    expect(round[1]).toMatchObject({ analysis, emotion: { label: "Sadness" }, latencyMs: 1 })
    expect(round[1]).not.toHaveProperty("fresh")
  })

  it("lượt safety bỏ cảm xúc và bài hát", () => {
    let s = sent(initialState("s", []))
    s = chatReducer(s, {
      type: "resolve",
      userId: "u1",
      botId: "b1",
      response: { ...response, safety: true },
      createdAt: "now",
    })
    expect(s.messages[0]).toMatchObject({ emotion: null })
    expect(s.messages[1]).toMatchObject({ safety: true, songs: [], emotion: null })
  })

  it("fail rồi retry rồi resolve", () => {
    let s = sent(initialState("s", []))
    s = chatReducer(s, { type: "fail", userId: "u1", error: "mạng" })
    expect(s.messages[0]).toMatchObject({ status: "error", error: "mạng" })
    expect(s.messages).toHaveLength(1)
    s = chatReducer(s, { type: "retry", userId: "u1" })
    expect(s.messages[0]).toMatchObject({ status: "sending" })
    s = chatReducer(s, { type: "resolve", userId: "u1", botId: "b1", response, createdAt: "now" })
    expect(s.messages.map((m) => m.role)).toEqual(["user", "bot"])
    expect(s.messages[0]).toMatchObject({ status: "sent" })
  })

  it("hydrate chỉ áp dụng khi cùng phiên và danh sách đang trống", () => {
    const msgs = turnsToMessages([turn("t1")])
    expect(chatReducer(initialState("s", []), { type: "hydrate", sessionId: "s", messages: msgs }).messages).toHaveLength(2)
    expect(chatReducer(initialState("s", []), { type: "hydrate", sessionId: "other", messages: msgs }).messages).toHaveLength(0)
    const busy = sent(initialState("s", []))
    expect(chatReducer(busy, { type: "hydrate", sessionId: "s", messages: msgs }).messages).toHaveLength(1)
  })

  it("switch thay phiên và danh sách", () => {
    const s = chatReducer(sent(initialState("s", [])), { type: "switch", sessionId: "n", messages: [] })
    expect(s).toEqual({ sessionId: "n", messages: [] })
  })
})

function turn(id: string, over: Partial<SessionTurn> = {}): SessionTurn {
  return {
    turn_id: id,
    user_text: "xin chào",
    reply: "chào bạn",
    emotion: response.emotion,
    songs: response.songs,
    safety: false,
    created_at: "2026-01-01T00:00:00Z",
    ...over,
  }
}

describe("turnsToMessages", () => {
  it("mỗi lượt thành tin người dùng + tin bot theo thứ tự", () => {
    const msgs = turnsToMessages([turn("t1"), turn("t2")])
    expect(msgs.map((m) => m.role)).toEqual(["user", "bot", "user", "bot"])
    expect(msgs[0]).toMatchObject({ status: "sent", emotion: { label: "Sadness" } })
  })
  it("lượt safety không có cảm xúc/bài hát", () => {
    const [u, b] = turnsToMessages([turn("t1", { safety: true })])
    expect(u).toMatchObject({ emotion: null })
    expect(b).toMatchObject({ songs: [], safety: true })
  })
})

describe("toStored", () => {
  it("bỏ tin chưa hoàn tất và cờ fresh, giới hạn 100 tin", () => {
    const many: ChatMessage[] = Array.from({ length: 120 }, (_, i) => ({
      id: `b${i}`,
      role: "bot",
      text: "x",
      status: "sent",
      createdAt: "n",
      songs: [],
      safety: false,
      replyTo: "u",
      fresh: true,
    }))
    const pendingMsg: ChatMessage = {
      id: "p",
      role: "user",
      text: "đang gửi",
      status: "sending",
      createdAt: "n",
      goal: null,
      emotion: null,
    }
    const out = toStored([...many, pendingMsg])
    expect(out).toHaveLength(MAX_STORED_MESSAGES)
    expect(out.some((m) => m.id === "p")).toBe(false)
    expect("fresh" in out[0]).toBe(false)
  })
})

describe("đánh giá", () => {
  it("resolve lưu turnId, rate đổi rating đúng tin bot", () => {
    let s = sent(initialState("s", []))
    s = chatReducer(s, { type: "resolve", userId: "u1", botId: "b1", response, createdAt: "now" })
    expect(s.messages[1]).toMatchObject({ turnId: "t1", rating: null })
    s = chatReducer(s, { type: "rate", botId: "b1", rating: "up" })
    expect(s.messages[1]).toMatchObject({ rating: "up" })
    expect(s.messages[0]).not.toHaveProperty("rating")
    s = chatReducer(s, { type: "rate", botId: "b1", rating: null })
    expect(s.messages[1]).toMatchObject({ rating: null })
  })

  it("turnsToMessages gắn turnId và toStored giữ rating", () => {
    const turn = { turn_id: "t9", user_text: "a", reply: "b", songs: [], safety: false, created_at: "x" }
    const msgs = turnsToMessages([turn as SessionTurn])
    expect(msgs[1]).toMatchObject({ turnId: "t9" })
    const rated = chatReducer(initialState("s", msgs), { type: "rate", botId: "t9-b", rating: "down" })
    expect(toStored(rated.messages)[1]).toMatchObject({ rating: "down", turnId: "t9" })
  })
})
