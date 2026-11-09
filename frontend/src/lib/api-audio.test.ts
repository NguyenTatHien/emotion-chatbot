import { afterEach, describe, expect, it, vi } from "vitest"
import { sendChat } from "./api"

afterEach(() => vi.unstubAllGlobals())

describe("sendChat với audio", () => {
  it("gửi audio_file và transcript_hint, không có message", async () => {
    const fn = vi.fn(async () => Response.json({ reply: "ok" }))
    vi.stubGlobal("fetch", fn)
    const blob = new Blob(["abc"], { type: "audio/webm" })
    await sendChat({
      sessionId: "s1",
      audio: { blob, filename: "voice.webm" },
      transcriptHint: "  mình hơi lo ",
    })
    const form = (fn.mock.calls[0] as unknown as [string, RequestInit])[1]
      .body as FormData
    const file = form.get("audio_file") as File
    expect(file.name).toBe("voice.webm")
    expect(file.size).toBe(3)
    expect(form.get("transcript_hint")).toBe("mình hơi lo")
    expect(form.has("message")).toBe(false)
  })

  it("bỏ transcript_hint khi rỗng", async () => {
    const fn = vi.fn(async () => Response.json({ reply: "ok" }))
    vi.stubGlobal("fetch", fn)
    await sendChat({
      sessionId: "s1",
      audio: { blob: new Blob(["a"]), filename: "voice.ogg" },
      transcriptHint: "   ",
    })
    const form = (fn.mock.calls[0] as unknown as [string, RequestInit])[1]
      .body as FormData
    expect(form.has("transcript_hint")).toBe(false)
  })
})
