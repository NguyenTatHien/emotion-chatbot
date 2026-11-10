import { useState } from "react"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"
import type { Song } from "@/lib/api"
import { SongList } from "./SongList"
import { playableIndexes, SongPlayerDialog } from "./SongPlayerDialog"

const song = (title: string, url: string): Song => ({
  title,
  artist: `Ca sĩ ${title}`,
  youtube_url: url,
  reason: "Hợp tâm trạng",
})

const SONGS: Song[] = [
  song("Một", "https://www.youtube.com/watch?v=aaaaaa1"),
  song("Không video", "https://example.com/bai-hat"),
  song("Hai", "https://youtu.be/bbbbbb2"),
  song("Ba", "https://www.youtube.com/watch?v=cccccc3"),
]

const iframeSrc = () =>
  within(screen.getByRole("dialog"))
    .getByTitle(/^Phát bài/)
    .getAttribute("src")

describe("SongPlayerDialog", () => {
  it("playableIndexes bỏ qua bài không có video YouTube", () => {
    expect(playableIndexes(SONGS)).toEqual([0, 2, 3])
  })

  it("bấm thẻ mở popup lớn, có tiêu đề, ca sĩ, vị trí 1/3", async () => {
    const user = userEvent.setup()
    render(<SongList songs={SONGS} />)
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Nghe bài Một" }))
    const dialog = await screen.findByRole("dialog", { name: "Một" })
    expect(within(dialog).getByText(/Ca sĩ Một/)).toBeInTheDocument()
    expect(within(dialog).getByText("1/3")).toBeInTheDocument()
    expect(iframeSrc()).toContain("/embed/aaaaaa1")
    expect(
      within(dialog).getByRole("button", { name: "Bài trước" })
    ).toBeDisabled()
  })

  it("nút tiếp/trước, phím mũi tên và dải bài chuyển đúng video", async () => {
    const user = userEvent.setup()
    render(<SongList songs={SONGS} />)
    await user.click(screen.getByRole("button", { name: "Nghe bài Một" }))
    const dialog = await screen.findByRole("dialog")

    await user.click(
      within(dialog).getByRole("button", { name: "Bài tiếp theo" })
    )
    expect(iframeSrc()).toContain("/embed/bbbbbb2")
    expect(within(dialog).getByText("2/3")).toBeInTheDocument()

    await user.keyboard("{ArrowRight}")
    expect(iframeSrc()).toContain("/embed/cccccc3")
    expect(
      within(dialog).getByRole("button", { name: "Bài tiếp theo" })
    ).toBeDisabled()

    await user.keyboard("{ArrowLeft}")
    expect(iframeSrc()).toContain("/embed/bbbbbb2")

    const strip = within(dialog).getByRole("list", {
      name: "Danh sách bài gợi ý",
    })
    expect(within(strip).getAllByRole("button")).toHaveLength(3)
    await user.click(
      within(strip).getByRole("button", { name: "Chuyển sang bài Một" })
    )
    expect(iframeSrc()).toContain("/embed/aaaaaa1")
    expect(
      within(strip).getByRole("button", { name: "Chuyển sang bài Một" })
    ).toHaveAttribute("aria-current", "true")
  })

  it("Esc hoặc nút đóng thì gỡ iframe (dừng phát)", async () => {
    const user = userEvent.setup()
    render(<SongList songs={SONGS} />)
    await user.click(screen.getByRole("button", { name: "Nghe bài Hai" }))
    await screen.findByRole("dialog")
    await user.keyboard("{Escape}")
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    )
    expect(document.querySelector("iframe")).toBeNull()

    await user.click(screen.getByRole("button", { name: "Nghe bài Ba" }))
    await user.click(
      await screen.findByRole("button", { name: "Đóng trình phát" })
    )
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    )
  })

  it("bài không có video vẫn mở tab mới, không mở popup", () => {
    render(<SongList songs={SONGS} />)
    expect(
      screen.getByRole("link", { name: "Mở bài Không video ở tab mới" })
    ).toHaveAttribute("href", "https://example.com/bai-hat")
  })

  it("chỉ có một bài: không hiện dải danh sách", async () => {
    function One() {
      const [i, setI] = useState<number | null>(0)
      return (
        <SongPlayerDialog songs={[SONGS[0]]} index={i} onIndexChange={setI} />
      )
    }
    render(<One />)
    const dialog = await screen.findByRole("dialog")
    expect(
      within(dialog).queryByRole("list", { name: "Danh sách bài gợi ý" })
    ).not.toBeInTheDocument()
  })
})
