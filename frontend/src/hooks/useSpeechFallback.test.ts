import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { FakeRecognition, installFakeSpeech } from "@/test/fake-media"
import { useSpeechFallback } from "./useSpeechFallback"

afterEach(() => vi.unstubAllGlobals())

describe("useSpeechFallback", () => {
  it("cấu hình vi-VN, continuous, interim và hiện chữ tạm thời rồi chữ cuối", () => {
    const instances = installFakeSpeech()
    const { result } = renderHook(() => useSpeechFallback())
    expect(result.current.supported).toBe(true)
    act(() => result.current.start())

    const rec = instances[0]
    expect(rec.lang).toBe("vi-VN")
    expect(rec.continuous).toBe(true)
    expect(rec.interimResults).toBe(true)
    expect(rec.started).toBe(1)

    act(() => rec.emit([["mình hơi", false]]))
    expect(result.current.text).toBe("mình hơi")
    act(() => rec.emit([["mình hơi lo", true]]))
    act(() =>
      rec.emit(
        [
          ["mình hơi lo", true],
          ["về bài thi", false],
        ],
        1
      )
    )
    expect(result.current.text).toBe("mình hơi lo về bài thi")

    let final = ""
    act(() => {
      final = result.current.stop()
    })
    expect(final).toBe("mình hơi lo về bài thi")
    expect(rec.stopped).toBe(true)
  })

  it("tự nối lại khi trình duyệt kết thúc sớm, dừng hẳn khi đã stop", () => {
    const instances = installFakeSpeech()
    const { result } = renderHook(() => useSpeechFallback())
    act(() => result.current.start())
    const rec = instances[0]
    act(() => rec.onend?.())
    expect(rec.started).toBe(2)

    act(() => {
      result.current.stop()
    })
    expect(rec.onend).toBeNull()
  })

  it("lỗi quyền thì không nối lại; mọi lỗi bị nuốt", () => {
    const instances = installFakeSpeech()
    const { result } = renderHook(() => useSpeechFallback())
    act(() => result.current.start())
    const rec = instances[0]
    expect(() =>
      act(() => rec.onerror?.({ error: "not-allowed" }))
    ).not.toThrow()
    act(() => rec.onend?.())
    expect(rec.started).toBe(1)
  })

  it("start() ném lỗi cũng không làm hỏng ghi âm", () => {
    class Broken extends FakeRecognition {
      start(): void {
        throw new Error("InvalidStateError")
      }
    }
    vi.stubGlobal("webkitSpeechRecognition", Broken)
    const { result } = renderHook(() => useSpeechFallback())
    expect(() => act(() => result.current.start())).not.toThrow()
    expect(result.current.text).toBe("")
  })

  it("trình duyệt không hỗ trợ: mọi hàm là no-op, không báo lỗi", () => {
    vi.stubGlobal("SpeechRecognition", undefined)
    vi.stubGlobal("webkitSpeechRecognition", undefined)
    const { result } = renderHook(() => useSpeechFallback())
    expect(result.current.supported).toBe(false)
    act(() => result.current.start())
    let final = "x"
    act(() => {
      final = result.current.stop()
    })
    expect(final).toBe("")
    expect(result.current.text).toBe("")
  })
})
