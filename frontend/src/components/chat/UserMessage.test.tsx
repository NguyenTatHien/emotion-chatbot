import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { Emotion } from "@/lib/api"
import type { UserMessage as UserMsg } from "@/hooks/chat-state"
import { UserMessage } from "./UserMessage"

const PROBS = {
  Anger: 0.35,
  Disgust: 0,
  Enjoyment: 0,
  Fear: 0,
  Other: 0.25,
  Sadness: 0.4,
  Surprise: 0,
}

function message(emotion: Emotion | null): UserMsg {
  return {
    id: "u1",
    role: "user",
    text: "hôm nay mệt quá",
    status: "sent",
    createdAt: "2026-01-01T00:00:00.000Z",
    goal: null,
    emotion,
    kind: "voice",
  }
}

const NOTE = /Theo lời nói/

describe("UserMessage: ghi chú late fusion", () => {
  it("nhãn bị đổi: hiện dòng Theo lời nói / kết hợp giọng", () => {
    render(
      <UserMessage
        onRetry={vi.fn()}
        message={message({
          label: "Anger",
          probs: PROBS,
          arousal: "high",
          label_text: "Sadness",
          probs_text: PROBS,
        })}
      />
    )
    expect(
      screen.getByText("Theo lời nói: Buồn · kết hợp giọng: Tức giận")
    ).toBeInTheDocument()
  })

  it("không có label_text (gõ chữ): không hiện dòng ghi chú", () => {
    render(
      <UserMessage
        onRetry={vi.fn()}
        message={message({ label: "Sadness", probs: PROBS, arousal: null })}
      />
    )
    expect(screen.queryByText(NOTE)).not.toBeInTheDocument()
  })

  it("label_text trùng label: không hiện dòng ghi chú", () => {
    render(
      <UserMessage
        onRetry={vi.fn()}
        message={message({
          label: "Sadness",
          probs: PROBS,
          arousal: "low",
          label_text: "Sadness",
          probs_text: PROBS,
        })}
      />
    )
    expect(screen.queryByText(NOTE)).not.toBeInTheDocument()
  })
})
