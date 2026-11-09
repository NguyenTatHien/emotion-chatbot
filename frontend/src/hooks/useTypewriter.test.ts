import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { TYPEWRITER_MAX_MS, splitChunks, useTypewriter } from "./useTypewriter"

function setReducedMotion(reduce: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: reduce && query.includes("reduce"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
}

describe("useTypewriter", () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => {
    vi.useRealTimers()
    setReducedMotion(false)
  })

  it("splitChunks giữ nguyên văn bản", () => {
    const t = "Mình  nghe đây,\nbạn kể tiếp nhé"
    expect(splitChunks(t).join("")).toBe(t)
  })

  it("hiện dần và đủ văn bản trong tối đa 1,5 giây", () => {
    setReducedMotion(false)
    const text = Array.from({ length: 80 }, (_, i) => `từ${i}`).join(" ")
    const { result } = renderHook(() => useTypewriter(text, true))
    expect(result.current.text.length).toBeLessThan(text.length)
    act(() => {
      vi.advanceTimersByTime(TYPEWRITER_MAX_MS + 100)
    })
    expect(result.current.text).toBe(text)
    expect(result.current.done).toBe(true)
  })

  it("reduced motion: hiện ngay toàn bộ", () => {
    setReducedMotion(true)
    const { result } = renderHook(() => useTypewriter("xin chào bạn", true))
    expect(result.current).toEqual({ text: "xin chào bạn", done: true })
  })

  it("không hiện dần khi enabled=false", () => {
    setReducedMotion(false)
    const { result } = renderHook(() => useTypewriter("xin chào bạn", false))
    expect(result.current.text).toBe("xin chào bạn")
  })
})
