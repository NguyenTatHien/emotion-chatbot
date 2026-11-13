import { CircleAlert, RotateCcw } from "lucide-react"
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import { Button } from "@/components/ui/button"
import { Message, MessageContent, MessageFooter } from "@/components/ui/message"
import { Spinner } from "@/components/ui/spinner"
import { ArousalChip, EmotionChip } from "@/components/emotion/EmotionChip"
import { emotionMeta } from "@/lib/emotion-meta"
import type { UserMessage as UserMsg } from "@/hooks/chat-state"
import { VoiceBubble } from "./VoiceBubble"

interface UserMessageProps {
  message: UserMsg
  onRetry: (id: string) => void
}

export function UserMessage({ message, onRetry }: UserMessageProps) {
  const { emotion } = message
  return (
    <Message align="end">
      <MessageContent>
        <Bubble
          align="end"
          variant={message.status === "error" ? "destructive" : "default"}
          className={
            "lg:max-w-[min(70%,44rem)]" +
            (message.status === "sending" ? " opacity-80" : "")
          }
        >
          <BubbleContent
            className={
              "rounded-2xl rounded-br-md px-4 py-2.5 text-base whitespace-pre-wrap lg:text-[17px]" +
              (message.status === "error"
                ? ""
                : " bg-linear-to-br from-(--user-bubble-from) to-(--user-bubble-to) text-white shadow-md shadow-primary/20")
            }
          >
            {message.kind === "voice" ? (
              <VoiceBubble
                audioUrl={message.audioUrl}
                durationMs={message.durationMs}
                transcript={message.text}
                pending={message.status === "sending"}
              />
            ) : (
              message.text
            )}
          </BubbleContent>
        </Bubble>
        {message.status === "sending" ? (
          <MessageFooter>
            <span className="flex items-center gap-1.5" role="status">
              <Spinner className="size-3" aria-hidden="true" />
              Đang gửi…
            </span>
          </MessageFooter>
        ) : null}
        {message.status === "error" ? (
          <MessageFooter className="flex-wrap gap-2 text-destructive">
            <span className="flex items-center gap-1.5" role="alert">
              <CircleAlert className="size-4" aria-hidden="true" />
              Gửi không được{message.error ? `: ${message.error}` : ""}
            </span>
            <Button
              type="button"
              variant="outline"
              className="min-h-11 min-w-11 gap-1.5 px-3 text-sm"
              onClick={() => onRetry(message.id)}
            >
              <RotateCcw aria-hidden="true" />
              Thử lại
            </Button>
          </MessageFooter>
        ) : null}
        {message.status === "sent" && emotion ? (
          <div className="flex flex-wrap items-center justify-end gap-2 self-end">
            <EmotionChip emotion={emotion} />
            {emotion.arousal ? <ArousalChip arousal={emotion.arousal} /> : null}
          </div>
        ) : null}
        {message.status === "sent" &&
        emotion?.label_text &&
        emotion.label_text !== emotion.label ? (
          <p className="self-end text-xs text-muted-foreground">
            Theo lời nói: {emotionMeta(emotion.label_text).vi} · kết hợp giọng:{" "}
            {emotionMeta(emotion.label).vi}
          </p>
        ) : null}
      </MessageContent>
    </Message>
  )
}
