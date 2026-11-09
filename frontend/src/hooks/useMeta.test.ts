import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { HEALTH_POLL_MS, useMeta } from "./useMeta"

const META = {
  labels: [],
  goals: [],
  modules: {},
  model_mode: "remote",
  llm_backend: "qwen",
}

let status: "up" | "down" = "up"
let visibility: DocumentVisibilityState = "visible"

function healthCalls(fn: ReturnType<typeof vi.fn>) {
  return fn.mock.calls.filter(([url]) => url === "/api/health").length
}

beforeEach(() => {
  vi.useFakeTimers()
  status = "up"
  visibility = "visible"
  vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

function stubFetch() {
  const fn = vi.fn(async (url: string) => {
    if (url === "/api/meta") return Response.json(META)
    if (url === "/api/health") return Response.json({ ok: true, model_server: status })
    return new Response("nf", { status: 404 })
  })
  vi.stubGlobal("fetch", fn)
  return fn
}

describe("useMeta health polling", () => {
  it("thăm ngay khi mount rồi mỗi 30 giây", async () => {
    const fn = stubFetch()
    const { result } = renderHook(() => useMeta())
    await act(async () => {})
    expect(result.current.modelServer).toBe("up")
    expect(healthCalls(fn)).toBe(1)

    status = "down"
    await act(async () => {
      await vi.advanceTimersByTimeAsync(HEALTH_POLL_MS)
    })
    expect(healthCalls(fn)).toBe(2)
    expect(result.current.modelServer).toBe("down")
  })

  it("tab ẩn thì không thăm; hiện lại thì thăm ngay", async () => {
    const fn = stubFetch()
    renderHook(() => useMeta())
    await act(async () => {})
    visibility = "hidden"
    await act(async () => {
      await vi.advanceTimersByTimeAsync(HEALTH_POLL_MS * 2)
    })
    expect(healthCalls(fn)).toBe(1)

    visibility = "visible"
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"))
    })
    expect(healthCalls(fn)).toBe(2)
  })

  it("dừng thăm khi unmount", async () => {
    const fn = stubFetch()
    const { unmount } = renderHook(() => useMeta())
    await act(async () => {})
    unmount()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(HEALTH_POLL_MS * 3)
    })
    expect(healthCalls(fn)).toBe(1)
  })
})
