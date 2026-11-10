import { ArrowDown } from "lucide-react"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller"
import type { ChatMessage } from "@/hooks/chat-state"
import type { Rating } from "@/lib/api"
import { BotMessage } from "./BotMessage"
import { TypingIndicator } from "./TypingIndicator"
import { UserMessage } from "./UserMessage"

interface MessageListProps {
  messages: ChatMessage[]
  pending: boolean
  onRetry: (id: string) => void
  onRate?: (id: string, rating: Rating) => void
}

export function MessageList({
  messages,
  pending,
  onRetry,
  onRate,
}: MessageListProps) {
  return (
    <MessageScrollerProvider defaultScrollPosition="end">
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
                scrollAnchor={m.role === "user"}
              >
                {m.role === "user" ? (
                  <UserMessage message={m} onRetry={onRetry} />
                ) : (
                  <BotMessage message={m} onRate={onRate} />
                )}
              </MessageScrollerItem>
            ))}
            {pending ? (
              <MessageScrollerItem messageId="typing">
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
