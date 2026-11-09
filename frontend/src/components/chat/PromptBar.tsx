import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react"
import { SendHorizontal } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { type RecorderError } from "@/hooks/useRecorder"
import {
  useVoiceRecording,
  type VoiceRecording,
} from "@/hooks/useVoiceRecording"
import type { Goal } from "@/lib/goals"
import { GoalPicker } from "./GoalPicker"
import { RecordButton } from "./RecordButton"
import { RecordingBar } from "./RecordingBar"

interface PromptBarProps {
  /** Trả true nếu tin đã được nhận gửi (để xoá ô nhập). */
  onSend: (text: string) => boolean
  goal: Goal | null
  onGoalChange: (goal: Goal | null) => void
  /** Trả true nếu tin giọng nói đã được nhận gửi. */
  onSendVoice: (voice: VoiceRecording) => boolean
  /** Đang chờ phản hồi: tạm khoá nút ghi âm. */
  busy?: boolean
}

const MAX_HEIGHT = 160
/** Bản ghi ngắn hơn mức này coi như bấm nhầm. */
const MIN_VOICE_MS = 500

export function PromptBar({
  onSend,
  goal,
  onGoalChange,
  onSendVoice,
  busy,
}: PromptBarProps) {
  const [text, setText] = useState("")
  const ref = useRef<HTMLTextAreaElement>(null)

  const handleVoice = useCallback(
    (voice: VoiceRecording) => {
      if (voice.durationMs < MIN_VOICE_MS) {
        toast.info("Bản ghi quá ngắn. Hãy ghi lâu hơn một chút rồi gửi.")
        return
      }
      onSendVoice(voice)
    },
    [onSendVoice]
  )
  const handleVoiceError = useCallback((error: RecorderError) => {
    toast.error(error.message)
  }, [])
  const voice = useVoiceRecording(handleVoice, handleVoiceError)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`
  }, [text])

  const submit = () => {
    if (!text.trim()) return
    if (onSend(text)) {
      setText("")
      ref.current?.focus()
    }
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // isComposing: không gửi nhầm khi đang gõ Telex/VNI bằng IME.
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form
      className="flex flex-col gap-2 border-t bg-background px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <GoalPicker value={goal} onChange={onGoalChange} />
      {voice.recording ? (
        <RecordingBar
          elapsedMs={voice.elapsedMs}
          maxMs={voice.maxMs}
          liveText={voice.liveText}
          stopping={voice.state === "stopping"}
          onCancel={voice.cancel}
          onSend={() => void voice.send()}
        />
      ) : (
        <div className="flex items-end gap-2">
          <RecordButton
            onClick={() => void voice.start()}
            disabled={busy}
            busy={voice.state === "requesting"}
          />
          <Textarea
            ref={ref}
            value={text}
            rows={1}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            aria-label="Nhập tin nhắn"
            placeholder="Nhập tin nhắn…"
            enterKeyHint="send"
            className="field-sizing-fixed max-h-40 min-h-11 flex-1 resize-none text-base md:text-base"
          />
          <Button
            type="submit"
            className="size-11 shrink-0 rounded-full"
            aria-label="Gửi tin nhắn"
            disabled={!text.trim()}
          >
            <SendHorizontal className="size-5" aria-hidden="true" />
          </Button>
        </div>
      )}
      <p className="text-center text-xs text-muted-foreground">
        Enter để gửi, Shift+Enter để xuống dòng. Đây không phải công cụ chẩn
        đoán tâm lý.
      </p>
    </form>
  )
}
