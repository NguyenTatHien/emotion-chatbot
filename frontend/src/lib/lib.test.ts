import { describe, expect, it } from "vitest"
import { EMOTION_LABELS, emotionMeta, percent } from "./emotion-meta"
import { GOALS, isGoal } from "./goals"
import { embedUrl, extractVideoId, thumbnailUrl } from "./youtube"

describe("emotion-meta", () => {
  it("có tên tiếng Việt đúng cho 7 nhãn", () => {
    expect(EMOTION_LABELS.map((l) => emotionMeta(l).vi)).toEqual([
      "Tức giận",
      "Khó chịu",
      "Vui vẻ",
      "Lo sợ",
      "Bình thường",
      "Buồn",
      "Ngạc nhiên",
    ])
  })
  it("nhãn lạ rơi về Other", () => {
    expect(emotionMeta("Whatever").vi).toBe("Bình thường")
  })
  it("làm tròn phần trăm", () => {
    expect(percent(0.616)).toBe(62)
    expect(percent(undefined)).toBe(0)
  })
})

describe("goals", () => {
  it("ánh xạ 4 mục tiêu", () => {
    expect(GOALS.map((g) => g.value)).toEqual([
      "xoa_diu",
      "nang_mood",
      "tap_trung",
      "giai_toa",
    ])
  })
  it("isGoal", () => {
    expect(isGoal("tap_trung")).toBe(true)
    expect(isGoal("x")).toBe(false)
    expect(isGoal(null)).toBe(false)
  })
})

describe("youtube", () => {
  it.each([
    ["https://www.youtube.com/watch?v=abc123", "abc123"],
    ["https://youtube.com/watch?v=dQw4w9WgXcQ&t=10", "dQw4w9WgXcQ"],
    ["https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://youtu.be/dQw4w9WgXcQ?si=x", "dQw4w9WgXcQ"],
    ["https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
    ["https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"],
  ])("trích id từ %s", (url, id) => {
    expect(extractVideoId(url)).toBe(id)
  })
  it.each([
    "",
    "không phải url",
    "https://example.com/watch?v=abc123",
    "https://www.youtube.com/watch",
    "https://www.youtube.com/watch?v=<script>",
    "https://www.youtube.com/playlist?list=PL1",
  ])("trả null cho %s", (url) => {
    expect(extractVideoId(url)).toBeNull()
  })
  it("dựng URL thumbnail và embed", () => {
    expect(thumbnailUrl("abc123")).toBe(
      "https://i.ytimg.com/vi/abc123/mqdefault.jpg"
    )
    expect(embedUrl("abc123")).toContain(
      "https://www.youtube-nocookie.com/embed/abc123"
    )
  })
})
