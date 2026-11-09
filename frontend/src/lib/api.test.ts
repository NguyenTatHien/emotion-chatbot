import { afterEach, describe, expect, it, vi } from "vitest"
import { ApiError, getSession, sendChat } from "./api"

function mockFetch(impl: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => impl(url, init))
  vi.stubGlobal("fetch", fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe("sendChat", () => {
  it("gửi FormData với session_id, message và goal", async () => {
    const fetchMock = mockFetch(() => Response.json({ reply: "ok" }))
    await sendChat({ sessionId: "s1", message: "hôm nay mệt quá", goal: "tap_trung" })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe("/api/chat")
    expect(init?.method).toBe("POST")
    const form = init?.body as FormData
    expect(form.get("session_id")).toBe("s1")
    expect(form.get("message")).toBe("hôm nay mệt quá")
    expect(form.get("goal")).toBe("tap_trung")
  })

  it("bỏ trường goal khi null", async () => {
    const fetchMock = mockFetch(() => Response.json({ reply: "ok" }))
    await sendChat({ sessionId: "s1", message: "a", goal: null })
    const form = fetchMock.mock.calls[0][1]?.body as FormData
    expect(form.has("goal")).toBe(false)
  })

  it("ném ApiError có status và detail khi HTTP >= 400", async () => {
    mockFetch(() => Response.json({ detail: "Tin nhắn quá dài" }, { status: 400 }))
    const err = await sendChat({ sessionId: "s", message: "a" }).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 400, detail: "Tin nhắn quá dài" })
  })

  it("lỗi mạng được ném nguyên", async () => {
    mockFetch(() => {
      throw new TypeError("Failed to fetch")
    })
    await expect(sendChat({ sessionId: "s", message: "a" })).rejects.toThrow("Failed to fetch")
  })
})

describe("getSession", () => {
  it("gọi đúng đường dẫn tương đối và mã hoá id", async () => {
    const fetchMock = mockFetch(() => Response.json({ session_id: "a b", turns: [] }))
    await getSession("a b")
    expect(fetchMock.mock.calls[0][0]).toBe("/api/session/a%20b")
  })
})
