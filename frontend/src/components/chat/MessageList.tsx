import { useEffect, useRef, useState } from "react"
import { ArrowDown } from "lucide-react"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
  useMessageScroller,
} from "@/components/ui/message-scroller"
import type { ChatMessage } from "@/hooks/chat-state"
import type { Rating } from "@/lib/api"
import { cn } from "@/lib/utils"
import { BotMessage } from "./BotMessage"
import { TypingIndicator } from "./TypingIndicator"
import { UserMessage } from "./UserMessage"

interface MessageListProps {
  messages: ChatMessage[]
  pending: boolean
  onRetry: (id: string) => void
  onRate?: (id: string, rating: Rating) => void
}

/** Hiệu ứng xuất hiện cho tin mới (tw-animate-css); tắt khi người dùng bật giảm chuyển động. */
const ENTER =
  "motion-safe:animate-in motion-safe:fade-in-0 motion-safe:slide-in-from-bottom-3 motion-safe:duration-300 motion-safe:ease-out"

/**
 * Khi người dùng gửi tin (hoặc bắt đầu chờ trả lời) thì cuộn mượt xuống cuối,
 * kể cả khi họ đang cuộn lên đọc tin cũ. Lúc bot "gõ" dần, autoScroll của
 * MessageScroller tự bám cuối nếu người dùng đang ở cuối.
 */
function FollowLatest({ trigger }: { trigger: string }) {
  const { scrollToEnd } = useMessageScroller()
  const first = useRef(true)
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    const frame = requestAnimationFrame(() =>
      scrollToEnd({ behavior: "smooth" })
    )
    return () => cancelAnimationFrame(frame)
  }, [trigger, scrollToEnd])
  return null
}

export function MessageList({
  messages,
  pending,
  onRetry,
  onRate,
}: MessageListProps) {
  // Tin có sẵn lúc mở (khôi phục từ lịch sử) thì không chạy hiệu ứng xuất hiện.
  const [initialIds] = useState(() => new Set(messages.map((m) => m.id)))
  const isNew = (id: string) => !initialIds.has(id)

  const lastUser = [...messages].reverse().find((m) => m.role === "user")
  const followTrigger = `${lastUser?.id ?? ""}:${pending}`

  return (
    <MessageScrollerProvider autoScroll defaultScrollPosition="end">
      <FollowLatest trigger={followTrigger} />
      <MessageScroller className="flex-1">
        <MessageScrollerViewport>
          <MessageScrollerContent
            aria-busy={pending}
            aria-label="Cuộc trò chuyện"
            role="log"
            aria-live="polite"
            className="mx-auto w-full max-w-5xl gap-6 px-4 py-6 sm:px-6 lg:px-10"
          >
            {messages.map((m) => (
              <MessageScrollerItem
                key={m.id}
                messageId={m.id}
                className={cn(isNew(m.id) && ENTER)}
              >
                {m.role === "user" ? (
                  <UserMessage message={m} onRetry={onRetry} />
                ) : (
                  <BotMessage message={m} onRate={onRate} />
                )}
              </MessageScrollerItem>
            ))}
            {pending ? (
              <MessageScrollerItem messageId="typing" className={ENTER}>
                <TypingIndicator />
              </MessageScrollerItem>
            ) : null}
          </MessageScrollerContent>
        </MessageScrollerViewport>
        <MessageScrollerButton className="size-11" size="icon-lg">
          <ArrowDown aria-hidden="true" />
          <span className="sr-only">Về tin mới nhất</span>
        </MessageScrollerButton>
      </MessageScroller>
    </MessageScrollerProvider>
  )
}
