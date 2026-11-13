import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { App } from "@/App"
import type { ChatResponse } from "@/lib/api"
import {
  installFakeMedia,
  installFakeSpeech,
  type FakeMedia,
} from "@/test/fake-media"

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

function voiceResponse(over: Partial<ChatResponse> = {}): ChatResponse {
  return {
    turn_id: "t1",
    reply: "Mình nghe bạn.",
    transcript: "hôm nay mệt quá",
    emotion: {
      label: "Sadness",
      probs: {
        Anger: 0,
        Disgust: 0,
        Enjoyment: 0,
        Fear: 0,
        Other: 0.3,
        Sadness: 0.7,
        Surprise: 0,
      },
      arousal: "high",
    },
    songs: [],
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

function installFetch(chat: (form: FormData) => Response | Promise<Response>) {
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

let media: FakeMedia
let createUrl: ReturnType<typeof vi.fn>
let revokeUrl: ReturnType<typeof vi.fn>

beforeEach(() => {
  window.matchMedia = ((query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
  createUrl = vi.fn(() => "blob:local-voice")
  revokeUrl = vi.fn()
  URL.createObjectURL = createUrl as unknown as typeof URL.createObjectURL
  URL.revokeObjectURL = revokeUrl as unknown as typeof URL.revokeObjectURL
})

afterEach(() => {
  media?.restore()
  vi.unstubAllGlobals()
})

describe("ghi âm trong ChatView", () => {
  it("ghi 8 giây rồi gửi: audio_file + transcript_hint, bong bóng giọng nói có transcript server", async () => {
    media = installFakeMedia()
    const speech = installFakeSpeech()
    const fetchMock = installFetch(() => Response.json(voiceResponse()))
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    expect(await screen.findByTestId("recording-bar")).toBeInTheDocument()
    // Ô nhập được thay bằng thanh ghi âm.
    expect(screen.queryByLabelText("Nhập tin nhắn")).not.toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Huỷ ghi âm" })
    ).toBeInTheDocument()
    expect(screen.getByRole("timer")).toHaveTextContent("0:00 / 0:30")

    // Chữ nhận dạng trực tiếp hiện trên thanh ghi âm.
    speech[0].emit([["hôm nay mệt", false]])
    expect(await screen.findByText("hôm nay mệt")).toBeInTheDocument()
    speech[0].emit([["hôm nay mệt quá", true]])

    media.advanceClock(8000)
    await user.click(screen.getByRole("button", { name: "Gửi ghi âm" }))

    await screen.findByText("Mình nghe bạn.")
    const calls = chatCalls(fetchMock)
    expect(calls).toHaveLength(1)
    const form = calls[0][1]?.body as FormData
    const file = form.get("audio_file") as File
    expect(file).toBeInstanceOf(Blob)
    expect(file.name).toBe("voice.webm")
    expect(form.get("transcript_hint")).toBe("hôm nay mệt quá")
    expect(form.has("message")).toBe(false)

    // Bong bóng: transcript của server, thời lượng 0:08, nút phát lại.
    expect(
      within(screen.getByRole("log")).getByText("hôm nay mệt quá")
    ).toBeInTheDocument()
    expect(screen.getByText("0:08")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Phát lại bản ghi" })
    ).toBeInTheDocument()
    // Micro đã được nhả, ô nhập chữ trở lại.
    expect(media.trackStop).toHaveBeenCalled()
    expect(screen.getByLabelText("Nhập tin nhắn")).toBeInTheDocument()
  })

  it("hiện transcript_hint trong lúc chờ phản hồi", async () => {
    media = installFakeMedia()
    const speech = installFakeSpeech()
    let release: (r: Response) => void = () => {}
    installFetch(() => new Promise<Response>((resolve) => (release = resolve)))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    await screen.findByTestId("recording-bar")
    speech[0].emit([["mình hơi lo", true]])
    media.advanceClock(3000)
    await user.click(screen.getByRole("button", { name: "Gửi ghi âm" }))
    expect(
      await within(await screen.findByRole("log")).findByText("mình hơi lo")
    ).toBeInTheDocument()
    release(Response.json(voiceResponse({ transcript: "mình hơi lo lắng" })))
    expect(await within(screen.getByRole("log")).findByText("mình hơi lo lắng")).toBeInTheDocument()
  })

  it("trình duyệt không có Web Speech: vẫn ghi và gửi, không có transcript_hint", async () => {
    media = installFakeMedia()
    vi.stubGlobal("SpeechRecognition", undefined)
    vi.stubGlobal("webkitSpeechRecognition", undefined)
    const fetchMock = installFetch(() => Response.json(voiceResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    await screen.findByTestId("recording-bar")
    media.advanceClock(2000)
    await user.click(screen.getByRole("button", { name: "Gửi ghi âm" }))
    await screen.findByText("Mình nghe bạn.")
    const form = chatCalls(fetchMock)[0][1]?.body as FormData
    expect(form.has("audio_file")).toBe(true)
    expect(form.has("transcript_hint")).toBe(false)
  })

  it("huỷ: không gửi gì, nhả micro, ô nhập chữ hiện lại và còn nguyên bản nháp", async () => {
    media = installFakeMedia()
    installFakeSpeech()
    const fetchMock = installFetch(() => Response.json(voiceResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByLabelText("Nhập tin nhắn"), "bản nháp")
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    await screen.findByTestId("recording-bar")
    await user.click(screen.getByRole("button", { name: "Huỷ ghi âm" }))

    expect(chatCalls(fetchMock)).toHaveLength(0)
    expect(media.trackStop).toHaveBeenCalled()
    expect(screen.queryByTestId("recording-bar")).not.toBeInTheDocument()
    expect(screen.getByLabelText("Nhập tin nhắn")).toHaveValue("bản nháp")
  })

  it("bản ghi quá ngắn (bấm nhầm) bị bỏ, có thông báo", async () => {
    media = installFakeMedia()
    installFakeSpeech()
    const fetchMock = installFetch(() => Response.json(voiceResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    await screen.findByTestId("recording-bar")
    media.advanceClock(100)
    await user.click(screen.getByRole("button", { name: "Gửi ghi âm" }))
    expect(await screen.findByText(/Bản ghi quá ngắn/)).toBeInTheDocument()
    expect(chatCalls(fetchMock)).toHaveLength(0)
  })

  it("từ chối quyền micro: toast lỗi, không có thanh ghi âm, vẫn gõ và gửi chữ", async () => {
    media = installFakeMedia({ getUserMediaError: "NotAllowedError" })
    const fetchMock = installFetch(() =>
      Response.json(voiceResponse({ transcript: null }))
    )
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))

    expect(
      await screen.findByText(/Bạn đã chặn quyền micro/)
    ).toBeInTheDocument()
    expect(screen.queryByTestId("recording-bar")).not.toBeInTheDocument()

    await user.type(
      screen.getByLabelText("Nhập tin nhắn"),
      "vẫn gõ được{Enter}"
    )
    await screen.findByText("Mình nghe bạn.")
    const form = chatCalls(fetchMock)[0][1]?.body as FormData
    expect(form.get("message")).toBe("vẫn gõ được")
  })

  it("không có MediaRecorder: toast nêu trình duyệt chưa hỗ trợ, ô gõ chữ giữ nguyên", async () => {
    media = installFakeMedia()
    vi.stubGlobal("MediaRecorder", undefined)
    installFetch(() => Response.json(voiceResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    expect(await screen.findByText(/chưa hỗ trợ ghi âm/)).toBeInTheDocument()
    expect(screen.getByLabelText("Nhập tin nhắn")).toBeEnabled()
  })

  it("lỗi mạng: tin giọng nói có Thử lại và gửi lại đúng bản ghi", async () => {
    media = installFakeMedia()
    installFakeSpeech()
    let fail = true
    const fetchMock = installFetch(() => {
      if (fail) throw new TypeError("Failed to fetch")
      return Response.json(voiceResponse())
    })
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    await screen.findByTestId("recording-bar")
    media.advanceClock(4000)
    await user.click(screen.getByRole("button", { name: "Gửi ghi âm" }))
    const retry = await screen.findByRole("button", { name: /Thử lại/ })
    fail = false
    await user.click(retry)
    await screen.findByText("Mình nghe bạn.")
    expect(chatCalls(fetchMock)).toHaveLength(2)
    const form = chatCalls(fetchMock)[1][1]?.body as FormData
    expect(form.has("audio_file")).toBe(true)
  })

  it("tải lại trang: tin giọng nói khôi phục thành transcript + icon micro, không lưu audioUrl", async () => {
    media = installFakeMedia()
    installFakeSpeech()
    installFetch(() => Response.json(voiceResponse()))
    const user = userEvent.setup()
    const first = render(<App />)
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    await screen.findByTestId("recording-bar")
    media.advanceClock(5000)
    await user.click(screen.getByRole("button", { name: "Gửi ghi âm" }))
    await screen.findByText("Mình nghe bạn.")

    const stored = Object.entries(localStorage).find(([k]) =>
      k.startsWith("ec.messages.")
    )
    expect(stored).toBeDefined()
    expect(stored![1]).not.toContain("blob:")
    expect(stored![1]).not.toContain("audioUrl")
    first.unmount()

    render(<App />)
    expect(
      within(screen.getByRole("log")).getByText("hôm nay mệt quá")
    ).toBeInTheDocument()
    expect(
      screen.getByRole("img", { name: "Tin giọng nói" })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Phát lại bản ghi" })
    ).not.toBeInTheDocument()
  })

  it("Cuộc trò chuyện mới thu hồi object URL của bản ghi", async () => {
    media = installFakeMedia()
    installFakeSpeech()
    installFetch(() => Response.json(voiceResponse()))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    await screen.findByTestId("recording-bar")
    media.advanceClock(5000)
    await user.click(screen.getByRole("button", { name: "Gửi ghi âm" }))
    await screen.findByText("Mình nghe bạn.")
    expect(createUrl).toHaveBeenCalledTimes(1)
    expect(revokeUrl).not.toHaveBeenCalled()

    await user.click(
      screen.getByRole("button", { name: "Cuộc trò chuyện mới" })
    )
    await waitFor(() =>
      expect(revokeUrl).toHaveBeenCalledWith("blob:local-voice")
    )
  })

  it("nút ghi âm, huỷ, gửi đạt 44px và có aria-label tiếng Việt", async () => {
    media = installFakeMedia()
    installFakeSpeech()
    installFetch(() => Response.json(voiceResponse()))
    const user = userEvent.setup()
    render(<App />)
    expect(screen.getByRole("button", { name: "Ghi âm" }).className).toContain(
      "size-11"
    )
    await user.click(screen.getByRole("button", { name: "Ghi âm" }))
    await screen.findByTestId("recording-bar")
    expect(
      screen.getByRole("button", { name: "Huỷ ghi âm" }).className
    ).toContain("size-11")
    expect(
      screen.getByRole("button", { name: "Gửi ghi âm" }).className
    ).toContain("size-11")
  })
})
