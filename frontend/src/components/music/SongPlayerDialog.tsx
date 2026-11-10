import { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight, ExternalLink, Music, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog"
import type { Song } from "@/lib/api"
import { cn } from "@/lib/utils"
import { embedUrl, extractVideoId, thumbnailUrl, watchUrl } from "@/lib/youtube"

interface SongPlayerDialogProps {
  songs: Song[]
  /** Vị trí bài đang phát trong `songs`; null = đóng. */
  index: number | null
  onIndexChange: (index: number | null) => void
}

/** Chỉ số các bài có video YouTube hợp lệ (phát được trong popup). */
export function playableIndexes(songs: Song[]): number[] {
  return songs.flatMap((s, i) => (extractVideoId(s.youtube_url) ? [i] : []))
}

function StripThumb({ id }: { id: string }) {
  const [failed, setFailed] = useState(false)
  return (
    <span className="relative block aspect-video w-full overflow-hidden rounded-lg bg-linear-to-br from-[color-mix(in_oklch,var(--mood)_65%,var(--card))] to-[color-mix(in_oklch,var(--aurora-accent)_45%,var(--card))]">
      {failed ? (
        <Music
          className="absolute inset-0 m-auto size-5 text-white/90"
          aria-hidden="true"
        />
      ) : (
        <img
          src={thumbnailUrl(id)}
          alt=""
          loading="lazy"
          onError={() => setFailed(true)}
          onLoad={(e) => {
            if (e.currentTarget.naturalWidth <= 120) setFailed(true)
          }}
          className="size-full object-cover"
        />
      )}
    </span>
  )
}

export function SongPlayerDialog({
  songs,
  index,
  onIndexChange,
}: SongPlayerDialogProps) {
  const playable = playableIndexes(songs)
  const pos = index === null ? -1 : playable.indexOf(index)
  const song = index === null ? null : songs[index]
  const id = song ? extractVideoId(song.youtube_url) : null
  const prev = pos > 0 ? playable[pos - 1] : null
  const next = pos >= 0 && pos < playable.length - 1 ? playable[pos + 1] : null

  const open = song !== null && id !== null

  // Phím ←/→ chuyển bài khi popup mở. Nghe ở window vì khi nút bị tắt (đầu/cuối
  // danh sách) trình duyệt có thể bỏ focus khỏi popup.
  useEffect(() => {
    if (!open) return
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "ArrowLeft" && prev !== null) {
        e.preventDefault()
        onIndexChange(prev)
      } else if (e.key === "ArrowRight" && next !== null) {
        e.preventDefault()
        onIndexChange(next)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, prev, next, onIndexChange])

  return (
    <Dialog
      open={open}
      onOpenChange={(open) => {
        if (!open) onIndexChange(null)
      }}
    >
      <DialogContent
        showCloseButton={false}
        overlayClassName="bg-black/75 supports-backdrop-filter:backdrop-blur-md"
        className="max-h-[calc(100dvh-1.5rem)] w-[min(calc(100vw-1.5rem),calc((100dvh-15rem)*16/9))] max-w-5xl min-w-[min(calc(100vw-1.5rem),22rem)] gap-0 overflow-x-hidden overflow-y-auto rounded-2xl border-0 bg-card p-0 shadow-2xl ring-1 ring-white/10 sm:max-w-5xl"
      >
        {song && id ? (
          <>
            <div className="aspect-video w-full bg-black">
              <iframe
                key={id}
                src={embedUrl(id)}
                title={`Phát bài ${song.title}`}
                className="size-full border-0"
                allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
                allowFullScreen
              />
            </div>

            <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-4 sm:px-5">
              <div className="min-w-0 flex-1">
                <DialogTitle className="truncate text-lg leading-tight font-semibold">
                  {song.title}
                </DialogTitle>
                <DialogDescription className="mt-1 truncate text-sm">
                  {song.artist}
                  {song.reason ? ` · ${song.reason}` : ""}
                </DialogDescription>
              </div>

              <div className="flex items-center gap-1.5">
                <Button
                  type="button"
                  variant="ghost"
                  className="size-11 cursor-pointer rounded-full"
                  aria-label="Bài trước"
                  disabled={prev === null}
                  onClick={() => prev !== null && onIndexChange(prev)}
                >
                  <ChevronLeft className="size-5" aria-hidden="true" />
                </Button>
                <span
                  className="min-w-10 text-center text-sm text-muted-foreground tabular-nums"
                  aria-live="polite"
                >
                  {pos + 1}/{playable.length}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  className="size-11 cursor-pointer rounded-full"
                  aria-label="Bài tiếp theo"
                  disabled={next === null}
                  onClick={() => next !== null && onIndexChange(next)}
                >
                  <ChevronRight className="size-5" aria-hidden="true" />
                </Button>
                <Button
                  asChild
                  variant="outline"
                  className="ml-auto h-11 cursor-pointer gap-1.5 rounded-full px-3 sm:ml-1 sm:px-4"
                >
                  <a
                    href={watchUrl(id)}
                    aria-label="Mở trên YouTube (tab mới)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="size-4" aria-hidden="true" />
                    <span className="sm:hidden">YouTube</span>
                    <span className="hidden sm:inline">Mở trên YouTube</span>
                  </a>
                </Button>
                <DialogClose asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    className="size-11 cursor-pointer rounded-full"
                    aria-label="Đóng trình phát"
                  >
                    <X className="size-5" aria-hidden="true" />
                  </Button>
                </DialogClose>
              </div>
            </div>

            {playable.length > 1 ? (
              <ul
                aria-label="Danh sách bài gợi ý"
                className="scroll-soft flex gap-3 overflow-x-auto border-t border-border/60 px-4 pt-3 pb-4 sm:px-5"
              >
                {playable.map((i) => {
                  const s = songs[i]
                  const sid = extractVideoId(s.youtube_url) as string
                  const active = i === index
                  return (
                    <li key={`${s.youtube_url}-${i}`} className="shrink-0">
                      <button
                        type="button"
                        onClick={() => onIndexChange(i)}
                        aria-current={active ? "true" : undefined}
                        aria-label={`Chuyển sang bài ${s.title}`}
                        className={cn(
                          "flex w-36 cursor-pointer flex-col gap-1.5 rounded-xl p-1.5 text-left transition-colors duration-200 outline-none focus-visible:ring-3 focus-visible:ring-ring/50 sm:w-40",
                          active
                            ? "bg-primary/10 ring-2 ring-primary"
                            : "hover:bg-muted"
                        )}
                      >
                        <StripThumb id={sid} />
                        <span className="truncate px-0.5 text-xs font-medium">
                          {s.title}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            ) : null}
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
