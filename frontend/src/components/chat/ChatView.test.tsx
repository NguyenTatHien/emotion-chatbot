import { render, screen, waitFor, within } from "@testing-library/react"
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
  model_mode: "mock",
  llm_backend: "mock",
}

function chatResponse(over: Partial<ChatResponse> = {}): ChatResponse {
  return {
    turn_id: "t1",
    reply: "Nghe có vẻ bạn đang buồn.",
    emotion: {
      label: "Sadness",
      probs: {
        Anger: 0.02,
        Disgust: 0.03,
        Enjoyment: 0.05,
        Fear: 0.04,
        Other: 0.2,
        Sadness: 0.62,
        Surprise: 0.04,
      },
      arousal: "low",
    },
    songs: [
      {
        title: "Bài thử",
        artist: "Ca sĩ thử",
        youtube_url: "https://www.youtube.com/watch?v=abc123",
        reason: "Nhẹ nhàng",
      },
    ],
    safety: false,
    meta: {
      llm_backend: "mock",
      model_mode: "mock",
      modules: {},
      degraded: false,
      latency_ms: 5,
      warnings: [],
      music_decision: "chip",
    },
    ...over,
  }
}

type ChatHandler = (form: FormData) => Response | Promise<Response>

function installFetch(chat: ChatHandler) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === "/api/meta") return Response.json(META)
    if (url.startsWith("/api/session/"))
      return Response.json({ session_id: "x", turns: [] })
    if (url === "/api/chat") return chat(init?.body as FormData)
    return new Response("not found", { status: 404 })
  })
  vi.stubGlobal("fetch", fn)
  return fn
}

const chatCalls = (fn: ReturnType<typeof installFetch>) =>
  fn.mock.calls.filter(([url]) => url === "/api/chat")

beforeEach(() => {
  // Tắt hiệu ứng hiện dần để test đọc được toàn bộ câu trả lời ngay.
  window.matchMedia = ((query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
})

afterEach(() => vi.unstubAllGlobals())

describe("ChatView", () => {
  it("gửi bằng Enter, xoá ô nhập, hiện chip Buồn 62% và bài hát", async () => {
    const fetchMock = installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    render(<App />)
    const input = screen.getByLabelText("Nhập tin nhắn")
    await user.type(input, "hôm nay mệt quá{Enter}")

    expect(input).toHaveValue("")
    await screen.findByText("Nghe có vẻ bạn đang buồn.")
    expect(
      within(screen.getByRole("log")).getByText("hôm nay mệt quá")
    ).toBeInTheDocument()
    expect(
      await screen.findByRole("button", { name: /Cảm xúc Buồn 62%/ })
    ).toHaveTextContent("Buồn 62%")
    expect(screen.getByText("kích động thấp")).toBeInTheDocument()

    const calls = chatCalls(fetchMock)
    expect(calls).toHaveLength(1)
    const form = calls[0][1]?.body as FormData
    expect(form.get("message")).toBe("hôm nay mệt quá")
    expect(form.get("session_id")).toBeTruthy()
    expect(form.has("goal")).toBe(false)
  })

  it("Shift+Enter xuống dòng và không gửi", async () => {
    const fetchMock = installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    render(<App />)
    const input = screen.getByLabelText("Nhập tin nhắn")
    await user.type(input, "dòng 1{Shift>}{Enter}{/Shift}dòng 2")
    expect(input).toHaveValue("dòng 1\ndòng 2")
    expect(chatCalls(fetchMock)).toHaveLength(0)
  })

  it("không gửi tin rỗng hoặc chỉ khoảng trắng", async () => {
    const fetchMock = installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "   {Enter}")
    expect(chatCalls(fetchMock)).toHaveLength(0)
    expect(screen.getByRole("button", { name: "Gửi tin nhắn" })).toBeDisabled()
  })

  it("bấm chip mở popover 7 xác suất và lưu ý", async () => {
    installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "buồn{Enter}")
    await user.click(
      await screen.findByRole("button", { name: /Cảm xúc Buồn/ })
    )
    const list = await screen.findByRole("list", {
      name: "Xác suất từng cảm xúc",
    })
    const rows = within(list).getAllByRole("listitem")
    expect(rows).toHaveLength(7)
    expect(rows[0]).toHaveTextContent("Buồn")
    expect(screen.getByText("Kết quả máy đoán, có thể sai")).toBeInTheDocument()
  })

  it("lượt safety hiện Alert, ẩn chip cảm xúc và bài hát", async () => {
    installFetch(() =>
      Response.json(
        chatResponse({
          safety: true,
          emotion: null,
          songs: [],
          reply: "Mình rất lo cho bạn. Hãy liên hệ người thân.",
        })
      )
    )
    const user = userEvent.setup()
    render(<App />)
    await user.type(
      screen.getByLabelText("Nhập tin nhắn"),
      "mình muốn chết{Enter}"
    )
    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent("Mình rất lo cho bạn")
    expect(
      screen.queryByRole("button", { name: /Cảm xúc/ })
    ).not.toBeInTheDocument()
    expect(screen.queryByText("Bài thử")).not.toBeInTheDocument()
  })

  it("lượt có bài hiện dòng dẫn phía trên danh sách", async () => {
    installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "buồn{Enter}")
    const lead = await screen.findByText("Vài bài có thể hợp với bạn lúc này")
    const section = screen.getByRole("region", { name: "Bài hát gợi ý" })
    expect(section).toContainElement(lead)
    expect(
      lead.compareDocumentPosition(within(section).getByRole("list")) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy()
  })

  it("lượt không có bài chỉ có câu trả lời, không có dòng dẫn và danh sách", async () => {
    installFetch(() =>
      Response.json(
        chatResponse({
          songs: [],
          reply: "Chào bạn, mình nghe đây.",
          meta: {
            ...chatResponse().meta,
            music_decision: "llm_no",
          },
        })
      )
    )
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "chào bạn{Enter}")
    expect(await screen.findByText("Chào bạn, mình nghe đây.")).toBeVisible()
    expect(
      screen.queryByText("Vài bài có thể hợp với bạn lúc này")
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole("region", { name: "Bài hát gợi ý" })
    ).not.toBeInTheDocument()
    expect(screen.queryByRole("list", { name: /Bài/ })).not.toBeInTheDocument()
  })

  it("chỉ tải iframe khi bấm thẻ bài hát", async () => {
    installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    const { container } = render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "buồn{Enter}")
    const play = await screen.findByRole("button", { name: "Nghe bài Bài thử" })
    expect(container.querySelector("iframe")).toBeNull()
    const thumb = screen.getByAltText("Ảnh bìa bài Bài thử")
    expect(thumb).toHaveAttribute(
      "src",
      "https://i.ytimg.com/vi/abc123/mqdefault.jpg"
    )
    expect(thumb).toHaveAttribute("loading", "lazy")
    await user.click(play)
    // Bấm thẻ mở popup trình phát (dialog nằm trong portal ngoài container).
    const dialog = await screen.findByRole("dialog", { name: "Bài thử" })
    const iframe = within(dialog).getByTitle("Phát bài Bài thử")
    expect(iframe.getAttribute("src")).toContain(
      "https://www.youtube-nocookie.com/embed/abc123"
    )
    expect(
      within(dialog).getByRole("link", { name: /Mở trên YouTube/ })
    ).toHaveAttribute("href", "https://www.youtube.com/watch?v=abc123")
  })

  it("lỗi mạng hiện Thử lại; thử lại thành công thêm câu trả lời", async () => {
    let fail = true
    installFetch(() => {
      if (fail) throw new TypeError("Failed to fetch")
      return Response.json(chatResponse())
    })
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "xin chào{Enter}")
    const retry = await screen.findByRole("button", { name: /Thử lại/ })
    expect(
      screen.queryByText("Nghe có vẻ bạn đang buồn.")
    ).not.toBeInTheDocument()
    fail = false
    await user.click(retry)
    await screen.findByText("Nghe có vẻ bạn đang buồn.")
    expect(
      screen.queryByRole("button", { name: /Thử lại/ })
    ).not.toBeInTheDocument()
  })

  it("HTTP 400 cũng là lỗi có Thử lại", async () => {
    installFetch(() =>
      Response.json({ detail: "Tin nhắn quá dài" }, { status: 400 })
    )
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "xin chào{Enter}")
    expect(
      await screen.findByRole("button", { name: /Thử lại/ })
    ).toBeInTheDocument()
    expect(screen.getByText(/Tin nhắn quá dài/)).toBeInTheDocument()
  })

  it("màn hình trống: bấm gợi ý sẽ gửi ngay câu đó", async () => {
    const fetchMock = installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.click(
      screen.getByRole("button", { name: "Hôm nay mình thấy mệt quá" })
    )
    await waitFor(() => expect(chatCalls(fetchMock)).toHaveLength(1))
    expect((chatCalls(fetchMock)[0][1]?.body as FormData).get("message")).toBe(
      "Hôm nay mình thấy mệt quá"
    )
  })

  it("mục tiêu: chọn thì gửi kèm, bấm lại thì bỏ chọn", async () => {
    const fetchMock = installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    render(<App />)
    const focus = screen.getByRole("radio", { name: "Tập trung" })
    await user.click(focus)
    expect(focus).toBeChecked()
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "một{Enter}")
    await screen.findByText("Nghe có vẻ bạn đang buồn.")
    expect((chatCalls(fetchMock)[0][1]?.body as FormData).get("goal")).toBe(
      "tap_trung"
    )

    await user.click(focus)
    expect(focus).not.toBeChecked()
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "hai{Enter}")
    await waitFor(() => expect(chatCalls(fetchMock)).toHaveLength(2))
    expect((chatCalls(fetchMock)[1][1]?.body as FormData).has("goal")).toBe(
      false
    )
  })

  it("khôi phục lịch sử từ localStorage sau khi tải lại", async () => {
    installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    const first = render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "lượt một{Enter}")
    await screen.findByText("Nghe có vẻ bạn đang buồn.")
    first.unmount()

    render(<App />)
    expect(
      within(screen.getByRole("log")).getByText("lượt một")
    ).toBeInTheDocument()
    expect(screen.getByText("Nghe có vẻ bạn đang buồn.")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /Cảm xúc Buồn 62%/ })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Nghe bài Bài thử" })
    ).toBeInTheDocument()
  })

  it("khôi phục từ GET /api/session khi localStorage trống", async () => {
    const fn = vi.fn(async (url: string) => {
      if (url === "/api/meta") return Response.json(META)
      if (url.startsWith("/api/session/"))
        return Response.json({
          session_id: "x",
          turns: [
            {
              turn_id: "t9",
              user_text: "câu cũ từ server",
              reply: "trả lời cũ",
              emotion: chatResponse().emotion,
              songs: [],
              safety: false,
              created_at: "2026-01-01T00:00:00Z",
            },
          ],
        })
      return new Response("", { status: 404 })
    })
    vi.stubGlobal("fetch", fn)
    render(<App />)
    expect(
      await within(await screen.findByRole("log")).findByText(
        "câu cũ từ server"
      )
    ).toBeInTheDocument()
    expect(screen.getByText("trả lời cũ")).toBeInTheDocument()
  })

  it("Cuộc trò chuyện mới xoá khung chat và đổi session_id", async () => {
    const fetchMock = installFetch(() => Response.json(chatResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "một{Enter}")
    await screen.findByText("Nghe có vẻ bạn đang buồn.")
    const oldId = (chatCalls(fetchMock)[0][1]?.body as FormData).get(
      "session_id"
    )

    await user.click(
      screen.getByRole("button", { name: "Cuộc trò chuyện mới" })
    )
    expect(
      screen.queryByText("Nghe có vẻ bạn đang buồn.")
    ).not.toBeInTheDocument()
    expect(
      screen.getByRole("heading", { name: "Chào bạn, mình ở đây để lắng nghe" })
    ).toBeInTheDocument()

    await user.type(screen.getByLabelText("Nhập tin nhắn"), "hai{Enter}")
    await waitFor(() => expect(chatCalls(fetchMock)).toHaveLength(2))
    const newId = (chatCalls(fetchMock)[1][1]?.body as FormData).get(
      "session_id"
    )
    expect(newId).not.toBe(oldId)
  })

  it("chế độ dự phòng: badge và tooltip liệt kê warnings", async () => {
    installFetch(() =>
      Response.json(
        chatResponse({
          meta: {
            ...chatResponse().meta,
            degraded: true,
            warnings: ["emotion: timeout"],
          },
        })
      )
    )
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "xin chào{Enter}")
    const badge = await screen.findByRole("button", { name: /chế độ dự phòng/ })
    expect(badge).toHaveTextContent("Dự phòng")
    await user.hover(badge)
    expect(
      (await screen.findAllByText("emotion: timeout")).length
    ).toBeGreaterThan(0)
  })

  it("aria-busy bật khi đang chờ phản hồi", async () => {
    let release: (r: Response) => void = () => {}
    installFetch(() => new Promise<Response>((resolve) => (release = resolve)))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "chờ{Enter}")
    const log = await screen.findByRole("log")
    expect(log).toHaveAttribute("aria-busy", "true")
    expect(screen.getByText("Bạn đồng hành đang soạn tin")).toBeInTheDocument()
    release(Response.json(chatResponse()))
    await screen.findByText("Nghe có vẻ bạn đang buồn.")
    expect(screen.getByRole("log")).toHaveAttribute("aria-busy", "false")
  })
})
