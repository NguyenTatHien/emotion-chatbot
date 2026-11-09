import { useState } from "react"
import { ExternalLink, Music, Play } from "lucide-react"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import type { Song } from "@/lib/api"
import { embedUrl, extractVideoId, thumbnailUrl, watchUrl } from "@/lib/youtube"

function Fallback() {
  return (
    <div className="flex size-full items-center justify-center bg-muted text-muted-foreground">
      <Music className="size-8" aria-hidden="true" />
    </div>
  )
}

export function SongCard({ song }: { song: Song }) {
  const id = extractVideoId(song.youtube_url)
  const [playing, setPlaying] = useState(false)
  const [thumbFailed, setThumbFailed] = useState(false)
  const openUrl = id ? watchUrl(id) : song.youtube_url

  const media = (
    <AspectRatio ratio={16 / 9} className="overflow-hidden rounded-lg">
      {id && playing ? (
        <iframe
          src={embedUrl(id)}
          title={`Phát bài ${song.title}`}
          className="size-full border-0"
          allow="autoplay; encrypted-media; picture-in-picture"
          allowFullScreen
        />
      ) : (
        <>
          {id && !thumbFailed ? (
            <img
              src={thumbnailUrl(id)}
              alt={`Ảnh bìa bài ${song.title}`}
              loading="lazy"
              onError={() => setThumbFailed(true)}
              className="size-full object-cover"
            />
          ) : (
            <Fallback />
          )}
          <span className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/20">
            <span className="flex size-11 items-center justify-center rounded-full bg-primary text-primary-foreground shadow">
              {id ? (
                <Play className="size-5" aria-hidden="true" />
              ) : (
                <ExternalLink className="size-5" aria-hidden="true" />
              )}
            </span>
          </span>
        </>
      )}
    </AspectRatio>
  )

  return (
    <article
      className="flex w-60 shrink-0 snap-start flex-col gap-2 rounded-xl border bg-card p-2 text-card-foreground"
      aria-label={`${song.title} - ${song.artist}`}
    >
      {id && playing ? (
        media
      ) : id ? (
        <button
          type="button"
          onClick={() => setPlaying(true)}
          aria-label={`Nghe bài ${song.title}`}
          className="relative block w-full rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {media}
        </button>
      ) : (
        <a
          href={openUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Mở bài ${song.title} ở tab mới`}
          className="relative block w-full rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {media}
        </a>
      )}
      <div className="flex min-w-0 flex-col gap-0.5 px-1">
        <p className="truncate text-sm font-semibold">{song.title}</p>
        <p className="truncate text-sm text-muted-foreground">{song.artist}</p>
        {song.reason ? (
          <p className="line-clamp-2 text-xs text-muted-foreground">
            {song.reason}
          </p>
        ) : null}
      </div>
      <a
        href={openUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto inline-flex min-h-11 items-center gap-1.5 rounded-md px-1 text-sm font-medium text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <ExternalLink className="size-4" aria-hidden="true" />
        Mở trên YouTube
      </a>
    </article>
  )
}
