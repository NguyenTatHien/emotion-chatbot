import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"
import { VoiceBubble } from "./VoiceBubble"

afterEach(() => vi.restoreAllMocks())

describe("VoiceBubble", () => {
  it("hiện transcript, thời lượng và nút phát lại bản ghi tại máy", async () => {
    const play = vi
      .spyOn(HTMLMediaElement.prototype, "play")
      .mockResolvedValue()
    const pause = vi
      .spyOn(HTMLMediaElement.prototype, "pause")
      .mockImplementation(() => {})
    const user = userEvent.setup()
    const { container } = render(
      <VoiceBubble
        audioUrl="blob:local-1"
        durationMs={8000}
        transcript="hôm nay mệt quá"
      />
    )
    expect(screen.getByText("hôm nay mệt quá")).toBeInTheDocument()
    expect(screen.getByText("0:08")).toBeInTheDocument()
    expect(container.querySelector("audio")).toHaveAttribute(
      "src",
      "blob:local-1"
    )

    const button = screen.getByRole("button", { name: "Phát lại bản ghi" })
    await user.click(button)
    expect(play).toHaveBeenCalledTimes(1)
    const pausing = screen.getByRole("button", { name: "Dừng phát bản ghi" })
    await user.click(pausing)
    expect(pause).toHaveBeenCalledTimes(1)
    expect(
      screen.getByRole("button", { name: "Phát lại bản ghi" })
    ).toBeInTheDocument()
  })

  it("play() bị từ chối thì nút trở lại trạng thái phát", async () => {
    vi.spyOn(HTMLMediaElement.prototype, "play").mockRejectedValue(
      new Error("NotAllowed")
    )
    const user = userEvent.setup()
    render(<VoiceBubble audioUrl="blob:x" durationMs={3000} transcript="a" />)
    await user.click(screen.getByRole("button", { name: "Phát lại bản ghi" }))
    expect(
      await screen.findByRole("button", { name: "Phát lại bản ghi" })
    ).toBeInTheDocument()
  })

  it("khôi phục sau khi tải lại: icon micro, transcript, không có nút phát", () => {
    const { container } = render(
      <VoiceBubble durationMs={12000} transcript="mình hơi lo" />
    )
    expect(
      screen.getByRole("img", { name: "Tin giọng nói" })
    ).toBeInTheDocument()
    expect(screen.getByText("mình hơi lo")).toBeInTheDocument()
    expect(screen.getByText("0:12")).toBeInTheDocument()
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
    expect(container.querySelector("audio")).toBeNull()
  })

  it("đang chờ server và chưa có chữ dự phòng", () => {
    render(
      <VoiceBubble audioUrl="blob:x" durationMs={2000} transcript="" pending />
    )
    expect(screen.getByText("Đang nhận dạng giọng nói…")).toBeInTheDocument()
  })

  it("nút phát đủ 44px", () => {
    render(<VoiceBubble audioUrl="blob:x" durationMs={2000} transcript="a" />)
    expect(
      screen.getByRole("button", { name: "Phát lại bản ghi" }).className
    ).toContain("size-11")
  })
})
