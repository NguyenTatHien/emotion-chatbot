import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { App } from "@/App"
import type { ChatResponse } from "@/lib/api"
import { groupConversations } from "./AppSidebar"
import { conversationTitle } from "./ChatView"

const META = {
  labels: ["Sadness", "Enjoyment", "Other"],
  goals: [],
  modules: {},
  model_mode: "mock",
  llm_backend: "mock",
}

function reply(text: string): ChatResponse {
  return {
    turn_id: `t-${text}`,
    reply: `trả lời ${text}`,
    emotion: {
      label: "Sadness",
      probs: { Sadness: 0.7, Enjoyment: 0.1, Other: 0.2 },
      arousal: null,
    },
    songs: [],
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
}

function installFetch() {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === "/api/meta") return Response.json(META)
    if (url.startsWith("/api/session/"))
      return Response.json({ session_id: "x", turns: [] })
    if (url === "/api/chat") {
      const text = String((init?.body as FormData).get("message"))
      return Response.json(reply(text))
    }
    return new Response("not found", { status: 404 })
  })
  vi.stubGlobal("fetch", fn)
  return fn
}

beforeEach(() => {
  window.matchMedia = ((query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
})

afterEach(() => vi.unstubAllGlobals())

// Nhiều lượt gõ phím: cho thời gian chờ rộng hơn mặc định 5 giây khi máy bận.
describe("Lịch sử trò chuyện ở sidebar", { timeout: 15_000 }, () => {
  it("cuộc cũ vẫn còn sau khi tạo cuộc mới và mở lại được", async () => {
    installFetch()
    const user = userEvent.setup()
    render(<App />)
    expect(screen.getByText(/Chưa có cuộc trò chuyện nào/)).toBeInTheDocument()

    await user.type(screen.getByLabelText("Nhập tin nhắn"), "cuộc một{Enter}")
    await screen.findByText("trả lời cuộc một")
    expect(
      await screen.findByRole("button", { name: "cuộc một" })
    ).toBeInTheDocument()

    await user.click(
      screen.getByRole("button", { name: "Cuộc trò chuyện mới" })
    )
    expect(screen.queryByText("trả lời cuộc một")).not.toBeInTheDocument()
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "cuộc hai{Enter}")
    await screen.findByText("trả lời cuộc hai")
    await screen.findByRole("button", { name: "cuộc hai" })

    await user.click(screen.getByRole("button", { name: "cuộc một" }))
    expect(await screen.findByText("trả lời cuộc một")).toBeInTheDocument()
    expect(screen.queryByText("trả lời cuộc hai")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "cuộc một" })).toHaveAttribute(
      "aria-current",
      "page"
    )
  })

  it("xoá cuộc đang mở: bỏ khỏi danh sách, xoá tin đã lưu, về màn hình chào", async () => {
    installFetch()
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "cần xoá{Enter}")
    await screen.findByText("trả lời cần xoá")

    await user.click(
      await screen.findByRole("button", {
        name: "Xoá cuộc trò chuyện: cần xoá",
      })
    )
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "cần xoá" })
      ).not.toBeInTheDocument()
    )
    expect(
      screen.getByRole("heading", { name: "Chào bạn, mình ở đây để lắng nghe" })
    ).toBeInTheDocument()
    const stored = Object.entries(localStorage).filter(
      ([k, v]) => k.startsWith("ec.messages.") && v.includes("cần xoá")
    )
    expect(stored).toHaveLength(0)
  })

  it("tải lại trang vẫn giữ danh sách", async () => {
    installFetch()
    const user = userEvent.setup()
    const first = render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "giữ lại{Enter}")
    await screen.findByText("trả lời giữ lại")
    first.unmount()

    render(<App />)
    expect(screen.getByRole("button", { name: "giữ lại" })).toBeInTheDocument()
  })
})

describe("conversationTitle", () => {
  it("lấy tin đầu của người dùng, gộp khoảng trắng và cắt 60 ký tự", () => {
    const long = "a ".repeat(50)
    const title = conversationTitle([
      {
        id: "1",
        role: "user",
        text: `  ${long}`,
        status: "sent",
        createdAt: "2026-11-10T00:00:00Z",
        goal: null,
        emotion: null,
      },
    ])
    expect(title.length).toBe(60)
    expect(title.endsWith("…")).toBe(true)
  })

  it("tin giọng nói chưa có chữ", () => {
    expect(
      conversationTitle([
        {
          id: "1",
          role: "user",
          text: "",
          kind: "voice",
          status: "sending",
          createdAt: "2026-11-10T00:00:00Z",
          goal: null,
          emotion: null,
        },
      ])
    ).toBe("Tin nhắn giọng nói")
  })
})

describe("groupConversations", () => {
  it("chia Hôm nay / 7 ngày qua / Cũ hơn và bỏ nhóm rỗng", () => {
    const now = new Date("2026-11-10T15:00:00")
    const groups = groupConversations(
      [
        { id: "a", title: "A", updatedAt: "2026-11-10T09:00:00" },
        { id: "b", title: "B", updatedAt: "2026-11-07T09:00:00" },
        { id: "c", title: "C", updatedAt: "2026-10-01T09:00:00" },
      ],
      now
    )
    expect(groups.map((g) => [g.label, g.items.map((i) => i.id)])).toEqual([
      ["Hôm nay", ["a"]],
      ["7 ngày qua", ["b"]],
      ["Cũ hơn", ["c"]],
    ])
    expect(
      groupConversations(
        [{ id: "a", title: "A", updatedAt: "2026-11-10T09:00:00" }],
        now
      ).map((g) => g.label)
    ).toEqual(["Hôm nay"])
  })
})
