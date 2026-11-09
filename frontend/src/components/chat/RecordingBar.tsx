import { SendHorizontal, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { formatClock } from "@/hooks/useRecorder"

interface RecordingBarProps {
  elapsedMs: number
  maxMs: number
  /** Chữ nhận dạng trực tiếp từ Web Speech API (rỗng nếu trình duyệt không có). */
  liveText: string
  onCancel: () => void
  onSend: () => void
  /** Đang dừng ghi để gửi. */
  stopping?: boolean
}

export function RecordingBar({
  elapsedMs,
  maxMs,
  liveText,
  onCancel,
  onSend,
  stopping,
}: RecordingBarProps) {
  return (
    <div
      className="flex min-h-11 items-center gap-2 rounded-3xl border bg-muted/40 py-0 pr-0 pl-1"
      data-testid="recording-bar"
    >
      <Button
        type="button"
        variant="ghost"
        className="size-11 shrink-0 rounded-full"
        aria-label="Huỷ ghi âm"
        onClick={onCancel}
      >
        <X className="size-5" aria-hidden="true" />
      </Button>
      <div className="flex min-w-0 flex-1 flex-col justify-center py-1.5">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="size-2.5 shrink-0 rounded-full bg-destructive motion-safe:animate-pulse"
          />
          <span
            className="text-sm font-medium tabular-nums"
            role="timer"
            aria-label="Thời gian ghi âm"
          >
            {formatClock(elapsedMs)} / {formatClock(maxMs)}
          </span>
          <span className="sr-only" role="status">
            Đang ghi âm
          </span>
        </div>
        {liveText ? (
          <p
            className="line-clamp-2 text-sm text-muted-foreground"
            aria-hidden="true"
          >
            {liveText}
          </p>
        ) : null}
      </div>
      <Button
        type="button"
        className="size-11 shrink-0 rounded-full"
        aria-label="Gửi ghi âm"
        disabled={stopping}
        onClick={onSend}
      >
        <SendHorizontal className="size-5" aria-hidden="true" />
      </Button>
    </div>
  )
}
