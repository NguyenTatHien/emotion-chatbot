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

function message(emotion: Emotion | null, over: Partial<UserMsg> = {}): UserMsg {
  return {
    id: "u1",
    role: "user",
    text: "hôm nay mệt quá",
    status: "sent",
    createdAt: "2026-01-01T00:00:00.000Z",
    goal: null,
    emotion,
    ...over,
  }
}

const FUSED: Emotion = {
  label: "Anger",
  probs: PROBS,
  arousal: "high",
  label_text: "Sadness",
  probs_text: PROBS,
}

describe("UserMessage: không dán nhãn cảm xúc", () => {
  it("tin đã gửi có emotion: không có chip cảm xúc, chip kích động hay phần trăm", () => {
    const { container } = render(
      <UserMessage onRetry={vi.fn()} message={message(FUSED)} />
    )
    expect(screen.getByText("hôm nay mệt quá")).toBeInTheDocument()
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
    expect(container).not.toHaveTextContent(
      /Buồn|Vui vẻ|Tức giận|Lo sợ|kích động|%/i
    )
  })

  it("không có dòng Theo lời nói / kết hợp giọng", () => {
    render(<UserMessage onRetry={vi.fn()} message={message(FUSED)} />)
    expect(screen.queryByText(/Theo lời nói/)).not.toBeInTheDocument()
    expect(screen.queryByText(/kết hợp giọng/)).not.toBeInTheDocument()
  })

  it("tin giọng nói vẫn hiện transcript", () => {
    render(
      <UserMessage
        onRetry={vi.fn()}
        message={message(FUSED, { kind: "voice", text: "mình mệt lắm" })}
      />
    )
    expect(screen.getByText("mình mệt lắm")).toBeInTheDocument()
    expect(screen.queryByText(/Theo lời nói/)).not.toBeInTheDocument()
  })
})
