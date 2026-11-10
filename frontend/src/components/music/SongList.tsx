import { useState } from "react"
import type { Song } from "@/lib/api"
import { cn } from "@/lib/utils"
import { SongCard } from "./SongCard"
import { SongPlayerDialog } from "./SongPlayerDialog"

/** Thẻ bài trượt vào lần lượt; tắt khi người dùng bật giảm chuyển động. */
const CARD_ENTER =
  "motion-safe:animate-in motion-safe:fade-in-0 motion-safe:zoom-in-95 motion-safe:slide-in-from-bottom-2 motion-safe:duration-300 motion-safe:ease-out motion-safe:fill-mode-both"
const CARD_STAGGER_MS = 70

export function SongList({
  songs,
  animate = false,
}: {
  songs: Song[]
  /** true với tin vừa nhận: các thẻ hiện lần lượt. */
  animate?: boolean
}) {
  // Bài đang mở trong popup trình phát; null = đóng.
  const [playing, setPlaying] = useState<number | null>(null)
  if (songs.length === 0) return null
  return (
    <section aria-label="Bài hát gợi ý" className="w-full max-w-full min-w-0">
      <ul className="scroll-soft -mx-1 flex snap-x snap-mandatory gap-3 overflow-x-auto px-1 pt-1 pb-3 md:mx-0 md:grid md:grid-cols-[repeat(auto-fill,minmax(12rem,1fr))] md:gap-4 md:overflow-visible md:px-0 md:pb-1">
        {songs.map((song, i) => (
          <li
            key={`${song.youtube_url}-${i}`}
            className={cn("flex shrink-0 md:min-w-0", animate && CARD_ENTER)}
            style={
              animate
                ? { animationDelay: `${i * CARD_STAGGER_MS}ms` }
                : undefined
            }
          >
            <SongCard song={song} onPlay={() => setPlaying(i)} />
          </li>
        ))}
      </ul>
      <SongPlayerDialog
        songs={songs}
        index={playing}
        onIndexChange={setPlaying}
      />
    </section>
  )
}
