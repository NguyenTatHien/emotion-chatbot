import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { SONG_LEAD_IN, SongList } from "./SongList"

const SONGS = [
  {
    title: "Kiss the Rain",
    artist: "Yiruma",
    youtube_url: "https://www.youtube.com/watch?v=imGaOIm5HOk",
    reason: "Bài nhạc không lời giúp tập trung",
  },
]

describe("SongList", () => {
  it("dùng dòng dẫn backend chọn theo mục tiêu", () => {
    render(<SongList songs={SONGS} lead="Vài bài giúp bạn tập trung" />)
    expect(screen.getByText("Vài bài giúp bạn tập trung")).toBeInTheDocument()
    expect(screen.queryByText(SONG_LEAD_IN)).not.toBeInTheDocument()
  })

  it("không có dòng dẫn từ backend thì dùng câu mặc định", () => {
    render(<SongList songs={SONGS} lead={null} />)
    expect(screen.getByText(SONG_LEAD_IN)).toBeInTheDocument()
  })

  it("không có bài thì không hiện gì", () => {
    const { container } = render(<SongList songs={[]} lead="Vài bài giúp bạn tập trung" />)
    expect(container).toBeEmptyDOMElement()
  })
})
