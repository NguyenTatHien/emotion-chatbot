import { describe, expect, it } from "vitest"
import type { ChatResponse, SessionTurn } from "@/lib/api"
import {
  audioUrlsOf,
  chatReducer,
  initialState,
  toStored,
  turnsToMessages,
  type UserMessage,
} from "./chat-state"

const response: ChatResponse = {
  turn_id: "t1",
  reply: "Mình nghe đây.",
  transcript: "hôm nay mệt quá",
  emotion: { label: "Sadness", probs: { Sadness: 0.7 }, arousal: "high" },
  songs: [],
  safety: false,
  meta: {
    llm_backend: "mock",
    model_mode: "mock",
    modules: {},
    degraded: false,
    latency_ms: 1,
    warnings: [],
  },
}

const voiceSent = () =>
  chatReducer(initialState("s", []), {
    type: "send",
    id: "u1",
    text: "chữ dự phòng",
    goal: null,
    createdAt: "now",
    voice: { audioUrl: "blob:abc", durationMs: 8000 },
  })

describe("tin giọng nói trong reducer", () => {
  it("send tạo tin kind=voice với audioUrl, thời lượng và chữ dự phòng", () => {
    const m = voiceSent().messages[0] as UserMessage
    expect(m).toMatchObject({
      kind: "voice",
      audioUrl: "blob:abc",
      durationMs: 8000,
      text: "chữ dự phòng",
      status: "sending",
    })
  })

  it("resolve thay chữ dự phòng bằng transcript của server", () => {
    const s = chatReducer(voiceSent(), {
      type: "resolve",
      userId: "u1",
      botId: "b1",
      response,
      createdAt: "now",
    })
    expect(s.messages[0]).toMatchObject({
      text: "hôm nay mệt quá",
      status: "sent",
    })
  })

  it("resolve giữ chữ dự phòng khi server không trả transcript", () => {
    const s = chatReducer(voiceSent(), {
      type: "resolve",
      userId: "u1",
      botId: "b1",
      response: { ...response, transcript: null },
      createdAt: "now",
    })
    expect(s.messages[0]).toMatchObject({ text: "chữ dự phòng" })
  })

  it("toStored bỏ audioUrl nhưng giữ transcript, kind và thời lượng", () => {
    const s = chatReducer(voiceSent(), {
      type: "resolve",
      userId: "u1",
      botId: "b1",
      response,
      createdAt: "now",
    })
    const stored = toStored(s.messages)
    expect(JSON.stringify(stored)).not.toContain("blob:abc")
    expect(stored[0]).toMatchObject({
      kind: "voice",
      durationMs: 8000,
      text: "hôm nay mệt quá",
    })
    expect(stored[0]).not.toHaveProperty("audioUrl")
  })

  it("audioUrlsOf liệt kê object URL cần thu hồi", () => {
    expect(audioUrlsOf(voiceSent().messages)).toEqual(["blob:abc"])
  })

  it("khôi phục từ backend: lượt có transcript là tin giọng nói", () => {
    const turn: SessionTurn = {
      turn_id: "t9",
      user_text: "hôm nay mệt quá",
      transcript: "hôm nay mệt quá",
      reply: "ok",
      emotion: null,
      songs: [],
      safety: false,
      created_at: "now",
    }
    const [user] = turnsToMessages([turn])
    expect(user).toMatchObject({
      role: "user",
      kind: "voice",
      text: "hôm nay mệt quá",
    })
  })
})
