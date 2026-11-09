import { useRef, useState } from "react"
import { Mic, Pause, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { formatClock } from "@/hooks/useRecorder"

interface VoiceBubbleProps {
  /** Object URL của bản ghi tại máy; không có khi tin được khôi phục sau khi tải lại trang. */
  audioUrl?: string
  durationMs?: number
  /** Transcript từ server (hoặc chữ dự phòng của trình duyệt khi đang chờ). */
  transcript: string
  /** Đang chờ server trả transcript. */
  pending?: boolean
}

export function VoiceBubble({
  audioUrl,
  durationMs = 0,
  transcript,
  pending,
}: VoiceBubbleProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)

  const toggle = () => {
    const el = audioRef.current
    if (!el) return
    if (playing) {
      el.pause()
      setPlaying(false)
      return
    }
    setPlaying(true)
    Promise.resolve(el.play()).catch(() => setPlaying(false))
  }

  const text = transcript.trim()
  return (
    <div className="flex min-w-48 flex-col gap-1.5" data-testid="voice-bubble">
      <div className="flex items-center gap-2">
        {audioUrl ? (
          <>
            <Button
              type="button"
              variant="secondary"
              className="size-11 shrink-0 rounded-full"
              aria-label={playing ? "Dừng phát bản ghi" : "Phát lại bản ghi"}
              aria-pressed={playing}
              onClick={toggle}
            >
              {playing ? (
                <Pause className="size-5" aria-hidden="true" />
              ) : (
                <Play className="size-5" aria-hidden="true" />
              )}
            </Button>
            <audio
              ref={audioRef}
              src={audioUrl}
              preload="metadata"
              onEnded={() => setPlaying(false)}
              onPause={() => setPlaying(false)}
              className="hidden"
            />
          </>
        ) : (
          <span
            className="flex size-11 shrink-0 items-center justify-center"
            role="img"
            aria-label="Tin giọng nói"
          >
            <Mic className="size-5" aria-hidden="true" />
          </span>
        )}
        <span className="text-sm tabular-nums" aria-label="Thời lượng">
          {formatClock(durationMs)}
        </span>
      </div>
      {text ? (
        <p className="text-base whitespace-pre-wrap">{text}</p>
      ) : (
        <p className="text-sm opacity-80">
          {pending ? "Đang nhận dạng giọng nói…" : "Không nhận dạng được chữ"}
        </p>
      )}
    </div>
  )
}
