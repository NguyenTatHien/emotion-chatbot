import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { installFakeMedia, type FakeMedia } from "@/test/fake-media"
import {
  RecorderError,
  filenameFor,
  formatClock,
  pickMimeType,
  useRecorder,
} from "./useRecorder"

let media: FakeMedia | null = null
afterEach(() => {
  media?.restore()
  media = null
  vi.useRealTimers()
})

describe("pickMimeType", () => {
  it("Chrome/Edge: ưu tiên webm opus", () => {
    media = installFakeMedia({
      supported: [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ],
    })
    expect(pickMimeType()).toBe("audio/webm;codecs=opus")
  })

  it("Firefox: không có webm opus thì dùng ogg opus", () => {
    media = installFakeMedia({ supported: ["audio/ogg;codecs=opus"] })
    expect(pickMimeType()).toBe("audio/ogg;codecs=opus")
  })

  it("Safari: chỉ có audio/mp4", () => {
    media = installFakeMedia({ supported: ["audio/mp4"] })
    expect(pickMimeType()).toBe("audio/mp4")
  })

  it("không loại nào được hỗ trợ: để trình duyệt tự chọn", () => {
    media = installFakeMedia({ supported: [] })
    expect(pickMimeType()).toBe("")
  })
})

describe("filenameFor và formatClock", () => {
  it("tên file theo mimeType", () => {
    expect(filenameFor("audio/webm;codecs=opus")).toBe("voice.webm")
    expect(filenameFor("audio/ogg;codecs=opus")).toBe("voice.ogg")
    expect(filenameFor("audio/mp4")).toBe("voice.m4a")
    expect(filenameFor("")).toBe("voice.webm")
  })

  it("đồng hồ m:ss", () => {
    expect(formatClock(0)).toBe("0:00")
    expect(formatClock(12_400)).toBe("0:12")
    expect(formatClock(30_000)).toBe("0:30")
    expect(formatClock(65_000)).toBe("1:05")
  })
})

describe("useRecorder", () => {
  it("ghi rồi dừng: trả blob đúng mimeType, thời lượng đo bằng performance.now, nhả micro", async () => {
    media = installFakeMedia({ supported: ["audio/ogg;codecs=opus"] })
    const { result } = renderHook(() => useRecorder())

    await act(async () => {
      await result.current.start()
    })
    expect(result.current.state).toBe("recording")
    expect(media.getUserMedia).toHaveBeenCalledWith({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: false },
    })
    expect(media.recorders[0].mimeType).toBe("audio/ogg;codecs=opus")
    expect(media.recorders[0].timeslice).toBe(250)

    media.advanceClock(8000)
    let recording: Awaited<ReturnType<typeof result.current.stop>> = null
    await act(async () => {
      recording = await result.current.stop()
    })
    expect(recording).not.toBeNull()
    expect(recording!.mimeType).toBe("audio/ogg;codecs=opus")
    expect(recording!.durationMs).toBe(8000)
    expect(recording!.blob.size).toBeGreaterThan(0)
    expect(media.trackStop).toHaveBeenCalled()
    expect(result.current.state).toBe("idle")
  })

  it("tự dừng ở 30 giây và gọi onAutoStop với thời lượng 30 giây", async () => {
    vi.useFakeTimers()
    media = installFakeMedia()
    const onAutoStop = vi.fn()
    const { result } = renderHook(() => useRecorder({ onAutoStop }))

    await act(async () => {
      await result.current.start()
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(29_900)
    })
    expect(onAutoStop).not.toHaveBeenCalled()
    expect(result.current.state).toBe("recording")

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200)
    })
    expect(onAutoStop).toHaveBeenCalledTimes(1)
    expect(onAutoStop.mock.calls[0][0]).toMatchObject({
      durationMs: 30_000,
      mimeType: "audio/webm;codecs=opus",
    })
    expect(result.current.state).toBe("idle")
    expect(media.trackStop).toHaveBeenCalled()
  })

  it("cancel nhả micro, không trả kết quả và không gọi onAutoStop", async () => {
    vi.useFakeTimers()
    media = installFakeMedia()
    const onAutoStop = vi.fn()
    const { result } = renderHook(() => useRecorder({ onAutoStop }))
    await act(async () => {
      await result.current.start()
    })
    act(() => result.current.cancel())
    expect(result.current.state).toBe("idle")
    expect(media.trackStop).toHaveBeenCalled()
    expect(media.recorders[0].state).toBe("inactive")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(40_000)
    })
    expect(onAutoStop).not.toHaveBeenCalled()
  })

  it("rời trang (unmount) khi đang ghi cũng nhả micro", async () => {
    media = installFakeMedia()
    const { result, unmount } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.start()
    })
    unmount()
    expect(media.trackStop).toHaveBeenCalled()
  })

  it("từ chối quyền -> RecorderError denied", async () => {
    media = installFakeMedia({ getUserMediaError: "NotAllowedError" })
    const { result } = renderHook(() => useRecorder())
    const err = await act(async () =>
      result.current.start().catch((e: unknown) => e)
    )
    expect(err).toBeInstanceOf(RecorderError)
    expect((err as RecorderError).kind).toBe("denied")
    expect((err as RecorderError).message).toContain("micro")
    expect(result.current.state).toBe("idle")
  })

  it("không có thiết bị -> no-device", async () => {
    media = installFakeMedia({ getUserMediaError: "NotFoundError" })
    const { result } = renderHook(() => useRecorder())
    const err = await act(async () =>
      result.current.start().catch((e: unknown) => e)
    )
    expect((err as RecorderError).kind).toBe("no-device")
  })

  it("trình duyệt không có MediaRecorder -> unsupported", async () => {
    media = installFakeMedia()
    vi.stubGlobal("MediaRecorder", undefined)
    const { result } = renderHook(() => useRecorder())
    const err = await act(async () =>
      result.current.start().catch((e: unknown) => e)
    )
    expect((err as RecorderError).kind).toBe("unsupported")
  })

  it("không ở secure context -> insecure", async () => {
    media = installFakeMedia()
    Object.defineProperty(window, "isSecureContext", {
      value: false,
      configurable: true,
    })
    try {
      const { result } = renderHook(() => useRecorder())
      const err = await act(async () =>
        result.current.start().catch((e: unknown) => e)
      )
      expect((err as RecorderError).kind).toBe("insecure")
      expect((err as RecorderError).message).toContain("HTTPS")
    } finally {
      Reflect.deleteProperty(window, "isSecureContext")
    }
  })
})
