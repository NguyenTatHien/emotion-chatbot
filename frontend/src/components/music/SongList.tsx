import type { Song } from "@/lib/api"
import { SongCard } from "./SongCard"

export function SongList({ songs }: { songs: Song[] }) {
  if (songs.length === 0) return null
  return (
    <section aria-label="Bài hát gợi ý" className="w-full max-w-full min-w-0">
      <ul className="scroll-soft -mx-1 flex snap-x snap-mandatory gap-3 overflow-x-auto px-1 pt-1 pb-3 md:mx-0 md:grid md:grid-cols-[repeat(auto-fill,minmax(12rem,1fr))] md:gap-4 md:overflow-visible md:px-0 md:pb-1">
        {songs.map((song, i) => (
          <li
            key={`${song.youtube_url}-${i}`}
            className="flex shrink-0 md:min-w-0"
          >
            <SongCard song={song} />
          </li>
        ))}
      </ul>
    </section>
  )
}
