import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { App } from "@/App"
import type { ChatResponse } from "@/lib/api"

const META = {
  labels: [
    "Anger",
    "Disgust",
    "Enjoyment",
    "Fear",
    "Other",
    "Sadness",
    "Surprise",
  ],
  goals: ["xoa_diu", "nang_mood", "tap_trung", "giai_toa"],
  modules: {},
  model_mode: "remote",
  llm_backend: "qwen",
}

function chatResponse(over: Partial<ChatResponse> = {}): ChatResponse {
  return {
    turn_id: "turn-1",
    reply: "Mình ở đây lắng nghe bạn.",
    emotion: {
      label: "Sadness",
      probs: { Sadness: 0.7, Other: 0.3 },
      arousal: "low",
    },
    songs: [],
    safety: false,
    meta: {
      llm_backend: "gemini",
      model_mode: "remote",
      modules: {},
      degraded: false,
      latency_ms: 5,
      warnings: [],
    },
    ...over,
  }
}

type FeedbackHandler = (
  body: Record<string, string>
) => Response | Promise<Response>

function installFetch(opts: {
  chat?: ChatResponse
  feedback?: FeedbackHandler
  health?: "up" | "down" | "n/a"
}) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === "/api/meta") return Response.json(META)
    if (url === "/api/health")
      return Response.json({ ok: true, model_server: opts.health ?? "n/a" })
    if (url.startsWith("/api/session/"))
      return Response.json({ session_id: "x", turns: [] })
    if (url === "/api/chat") return Response.json(opts.chat ?? chatResponse())
    if (url === "/api/feedback")
      return opts.feedback!(
        JSON.parse(init?.body as string) as Record<string, string>
      )
    return new Response("not found", { status: 404 })
  })
  vi.stubGlobal("fetch", fn)
  return fn
}

const feedbackCalls = (fn: ReturnType<typeof installFetch>) =>
  fn.mock.calls.filter(([url]) => url === "/api/feedback")

beforeEach(() => {
  window.matchMedia = ((query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
})

afterEach(() => vi.unstubAllGlobals())

async function sendOne(user: ReturnType<typeof userEvent.setup>) {
  render(<App />)
  await user.type(screen.getByLabelText("Nhập tin nhắn"), "buồn quá{Enter}")
  await screen.findByText("Mình ở đây lắng nghe bạn.")
}

describe("Nút đánh giá", () => {
  it("bấm Hữu ích gửi đúng nội dung và giữ aria-pressed", async () => {
    const fetchMock = installFetch({
      feedback: () => Response.json({ ok: true }),
    })
    const user = userEvent.setup()
    await sendOne(user)

    const up = screen.getByRole("button", { name: "Hữu ích" })
    const down = screen.getByRole("button", { name: "Chưa hợp" })
    expect(up).toHaveAttribute("aria-pressed", "false")
    await user.click(up)

    expect(up).toHaveAttribute("aria-pressed", "true")
    expect(down).toHaveAttribute("aria-pressed", "false")
    const calls = feedbackCalls(fetchMock)
    expect(calls).toHaveLength(1)
    const body = JSON.parse(calls[0][1]?.body as string)
    expect(body).toMatchObject({ turn_id: "turn-1", rating: "up" })
    expect(body.session_id).toBeTruthy()
    expect(JSON.stringify(body)).not.toContain("buồn quá")
  })

  it("đổi đánh giá gửi hai request và nút Chưa hợp được nhấn", async () => {
    const fetchMock = installFetch({
      feedback: () => Response.json({ ok: true }),
    })
    const user = userEvent.setup()
    await sendOne(user)
    await user.click(screen.getByRole("button", { name: "Hữu ích" }))
    await user.click(screen.getByRole("button", { name: "Chưa hợp" }))

    expect(feedbackCalls(fetchMock)).toHaveLength(2)
    expect(screen.getByRole("button", { name: "Chưa hợp" })).toHaveAttribute(
      "aria-pressed",
      "true"
    )
    expect(screen.getByRole("button", { name: "Hữu ích" })).toHaveAttribute(
      "aria-pressed",
      "false"
    )
  })

  it("bấm lại nút đang chọn không gửi thêm", async () => {
    const fetchMock = installFetch({
      feedback: () => Response.json({ ok: true }),
    })
    const user = userEvent.setup()
    await sendOne(user)
    await user.click(screen.getByRole("button", { name: "Hữu ích" }))
    await user.click(screen.getByRole("button", { name: "Hữu ích" }))
    expect(feedbackCalls(fetchMock)).toHaveLength(1)
  })

  it("cập nhật ngay (optimistic) rồi hoàn tác và báo lỗi khi gửi thất bại", async () => {
    let release!: (r: Response) => void
    installFetch({
      feedback: () => new Promise<Response>((resolve) => (release = resolve)),
    })
    const user = userEvent.setup()
    await sendOne(user)
    const up = screen.getByRole("button", { name: "Hữu ích" })
    await user.click(up)
    expect(up).toHaveAttribute("aria-pressed", "true") // chưa có phản hồi mà đã nhấn

    release(Response.json({ detail: "lỗi" }, { status: 500 }))
    await waitFor(() => expect(up).toHaveAttribute("aria-pressed", "false"))
    expect(
      await screen.findByText(/Chưa gửi được đánh giá/)
    ).toBeInTheDocument()
  })

  it("lỗi mạng cũng hoàn tác về lựa chọn trước đó", async () => {
    let fail = false
    installFetch({
      feedback: () => {
        if (fail) throw new TypeError("Failed to fetch")
        return Response.json({ ok: true })
      },
    })
    const user = userEvent.setup()
    await sendOne(user)
    await user.click(screen.getByRole("button", { name: "Hữu ích" }))
    fail = true
    await user.click(screen.getByRole("button", { name: "Chưa hợp" }))
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Hữu ích" })).toHaveAttribute(
        "aria-pressed",
        "true"
      )
    )
    expect(screen.getByRole("button", { name: "Chưa hợp" })).toHaveAttribute(
      "aria-pressed",
      "false"
    )
  })

  it("lượt an toàn không có nút đánh giá", async () => {
    installFetch({
      chat: chatResponse({
        safety: true,
        emotion: null,
        reply: "Mình rất lo cho bạn.",
      }),
      feedback: () => Response.json({ ok: true }),
    })
    const user = userEvent.setup()
    render(<App />)
    await user.type(
      screen.getByLabelText("Nhập tin nhắn"),
      "mình muốn chết{Enter}"
    )
    await screen.findByRole("alert")
    expect(
      screen.queryByRole("button", { name: "Hữu ích" })
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Chưa hợp" })
    ).not.toBeInTheDocument()
  })
})

describe("Trạng thái máy chủ", () => {
  it("hiện nguồn trả lời của lượt gần nhất và trạng thái model server", async () => {
    installFetch({
      health: "down",
      feedback: () => Response.json({ ok: true }),
    })
    const user = userEvent.setup()
    await sendOne(user)
    expect(
      await screen.findByRole("status", {
        name: "Máy chủ mô hình đang ngắt kết nối",
      })
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText("Nguồn trả lời gần nhất: Gemini")
    ).toBeInTheDocument()
  })

  it("model server sống hiện huy hiệu hoạt động", async () => {
    installFetch({ health: "up" })
    render(<App />)
    expect(
      await screen.findByRole("status", { name: "Máy chủ mô hình hoạt động" })
    ).toBeInTheDocument()
  })

  it("n/a thì không hiện huy hiệu model server", async () => {
    installFetch({ health: "n/a" })
    render(<App />)
    await screen.findByText("Đang hoạt động")
    expect(
      screen.queryByRole("status", { name: /Máy chủ mô hình/ })
    ).not.toBeInTheDocument()
  })
})
