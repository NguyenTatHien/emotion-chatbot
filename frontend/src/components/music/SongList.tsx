import type { Song } from "@/lib/api"
import { SongCard } from "./SongCard"

export function SongList({ songs }: { songs: Song[] }) {
  if (songs.length === 0) return null
  return (
    <section aria-label="Bài hát gợi ý" className="min-w-0 max-w-full">
      <ul className="-mx-1 flex snap-x snap-mandatory gap-3 overflow-x-auto px-1 pb-2">
        {songs.map((song, i) => (
          <li key={`${song.youtube_url}-${i}`} className="flex shrink-0">
            <SongCard song={song} />
          </li>
        ))}
      </ul>
    </section>
  )
}
