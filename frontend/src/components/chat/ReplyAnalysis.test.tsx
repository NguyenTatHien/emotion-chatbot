import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"
import type { Analysis, Emotion } from "@/lib/api"
import { ReplyAnalysis } from "./ReplyAnalysis"

const PROBS = {
  Anger: 0.05,
  Disgust: 0.03,
  Enjoyment: 0.04,
  Fear: 0.1,
  Other: 0.2,
  Sadness: 0.55,
  Surprise: 0.03,
}

const EMOTION: Emotion = { label: "Sadness", probs: PROBS, arousal: null }

const ANALYSIS: Analysis = {
  turn: 3,
  recent_emotions: [
    { turn: 1, label: "Sadness" },
    { turn: 2, label: "Fear" },
  ],
  last_music_turn: 1,
  tone: { key: "sad", text: "Chậm, dịu, ghi nhận cảm xúc trước." },
  music_reason: "Chưa cần gợi ý nhạc ở lượt này",
  emotion_source: "module",
}

function detailsOf() {
  return screen.getByText(/^Đã phân tích/).closest("details") as HTMLDetailsElement
}

describe("ReplyAnalysis", () => {
  it("mặc định thu gọn, tiêu đề có số giây một chữ số thập phân dấu phẩy", () => {
    render(<ReplyAnalysis analysis={ANALYSIS} emotion={EMOTION} latencyMs={1234} />)
    expect(screen.getByText("Đã phân tích · 1,2 giây")).toBeInTheDocument()
    expect(detailsOf().open).toBe(false)
  })

  it("dùng phần tử summary bàn phím truy cập được", () => {
    render(<ReplyAnalysis analysis={ANALYSIS} emotion={EMOTION} latencyMs={1234} />)
    expect(screen.getByText(/^Đã phân tích/).closest("summary")).not.toBeNull()
  })

  it("bấm mở: 3 nhãn cao nhất bằng tên tiếng Việt, dòng Khác, Cách trả lời và Nhạc", async () => {
    const user = userEvent.setup()
    render(<ReplyAnalysis analysis={ANALYSIS} emotion={EMOTION} latencyMs={900} />)
    await user.click(screen.getByText(/^Đã phân tích/))
    const details = detailsOf()
    expect(details.open).toBe(true)

    const list = within(details).getByRole("list", {
      name: "Xác suất các cảm xúc chính",
    })
    const rows = within(list).getAllByRole("listitem")
    expect(rows).toHaveLength(4)
    expect(rows[0]).toHaveTextContent("Buồn")
    expect(rows[0]).toHaveTextContent("55%")
    expect(rows[1]).toHaveTextContent("Bình thường")
    expect(rows[2]).toHaveTextContent("Lo sợ")
    expect(rows[3]).toHaveTextContent("Khác 15%")

    expect(details).toHaveTextContent("Chậm, dịu, ghi nhận cảm xúc trước.")
    expect(details).toHaveTextContent("Chưa cần gợi ý nhạc ở lượt này")
    expect(details).toHaveTextContent("Không phát hiện rủi ro")
  })

  it("các mục theo đúng thứ tự", () => {
    render(
      <ReplyAnalysis
        analysis={ANALYSIS}
        emotion={{ ...EMOTION, arousal: "high" }}
        latencyMs={1000}
      />
    )
    const titles = within(detailsOf())
      .getAllByRole("heading", { level: 4 })
      .map((h) => h.textContent)
    expect(titles).toEqual([
      "An toàn",
      "Cảm xúc",
      "Giọng nói",
      "Ngữ cảnh",
      "Cách trả lời",
      "Nhạc",
    ])
  })

  it("ngữ cảnh: lượt thứ N, cảm xúc các lượt gần và lượt gợi ý nhạc gần nhất", () => {
    render(<ReplyAnalysis analysis={ANALYSIS} emotion={EMOTION} latencyMs={1000} />)
    const details = detailsOf()
    expect(details).toHaveTextContent("Lượt thứ 3")
    expect(details).toHaveTextContent("lượt 1 Buồn; lượt 2 Lo sợ")
    expect(details).toHaveTextContent("Gợi ý nhạc gần nhất: lượt 1")
  })

  it("ngữ cảnh: chưa gợi ý nhạc lần nào, lượt an toàn trước đó là nội dung nhạy cảm", () => {
    render(
      <ReplyAnalysis
        analysis={{
          ...ANALYSIS,
          turn: 2,
          recent_emotions: [{ turn: 1, label: "safety" }],
          last_music_turn: null,
        }}
        emotion={EMOTION}
        latencyMs={1000}
      />
    )
    const details = detailsOf()
    expect(details).toHaveTextContent("lượt 1 nội dung nhạy cảm")
    expect(details).toHaveTextContent("Chưa gợi ý nhạc lần nào")
  })

  it("mục Giọng nói chỉ có khi có arousal", () => {
    const { rerender } = render(
      <ReplyAnalysis analysis={ANALYSIS} emotion={EMOTION} latencyMs={1000} />
    )
    expect(within(detailsOf()).queryByText("Giọng nói")).not.toBeInTheDocument()
    rerender(
      <ReplyAnalysis
        analysis={ANALYSIS}
        emotion={{ ...EMOTION, arousal: "medium" }}
        latencyMs={1000}
      />
    )
    expect(detailsOf()).toHaveTextContent("Kích động vừa")
  })

  it("giọng đổi nhãn: hiện theo lời nói và kết hợp giọng", () => {
    render(
      <ReplyAnalysis
        analysis={ANALYSIS}
        emotion={{
          label: "Anger",
          probs: PROBS,
          arousal: "high",
          label_text: "Sadness",
          probs_text: PROBS,
        }}
        latencyMs={1000}
      />
    )
    expect(detailsOf()).toHaveTextContent(
      "Kích động cao · theo lời nói: Buồn → kết hợp giọng: Tức giận"
    )
  })

  it("label_text trùng label: không thêm phần fusion", () => {
    render(
      <ReplyAnalysis
        analysis={ANALYSIS}
        emotion={{ ...EMOTION, arousal: "low", label_text: "Sadness", probs_text: PROBS }}
        latencyMs={1000}
      />
    )
    expect(detailsOf()).toHaveTextContent("Kích động thấp")
    expect(detailsOf()).not.toHaveTextContent("theo lời nói")
  })

  it("lượt safety: chỉ có An toàn và Nhạc, không có thanh cảm xúc", () => {
    render(
      <ReplyAnalysis
        safety
        analysis={{
          ...ANALYSIS,
          tone: null,
          emotion_source: null,
          music_reason: "Không gợi ý nhạc ở lượt cần hỗ trợ an toàn",
        }}
        emotion={null}
        latencyMs={1000}
      />
    )
    const details = detailsOf()
    expect(
      within(details)
        .getAllByRole("heading", { level: 4 })
        .map((h) => h.textContent)
    ).toEqual(["An toàn", "Nhạc"])
    expect(details).toHaveTextContent("Phát hiện nội dung cần hỗ trợ")
    expect(details).toHaveTextContent("Không gợi ý nhạc ở lượt cần hỗ trợ an toàn")
    expect(within(details).queryByRole("list")).not.toBeInTheDocument()
  })

  it("emotion dự phòng: ghi mô hình tạm không khả dụng và không vẽ thanh %", () => {
    render(
      <ReplyAnalysis
        analysis={{ ...ANALYSIS, emotion_source: "fallback" }}
        emotion={EMOTION}
        latencyMs={1000}
      />
    )
    const details = detailsOf()
    expect(details).toHaveTextContent("Mô hình cảm xúc tạm không khả dụng")
    expect(within(details).queryByRole("list", { name: /cảm xúc chính/ })).toBeNull()
    expect(within(details).queryByRole("progressbar")).not.toBeInTheDocument()
  })

  it("thiếu latency thì tiêu đề không có số giây", () => {
    render(<ReplyAnalysis analysis={ANALYSIS} emotion={EMOTION} />)
    expect(screen.getByText("Đã phân tích")).toBeInTheDocument()
  })
})
