import { Message, MessageAvatar, MessageContent } from "@/components/ui/message"
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import { BotAvatar } from "./BotAvatar"

export function TypingIndicator() {
  return (
    <Message role="status">
      <MessageAvatar>
        <BotAvatar />
      </MessageAvatar>
      <MessageContent>
        <Bubble variant="muted">
          <BubbleContent className="flex items-center gap-1 py-3">
            <span className="sr-only">Bạn đồng hành đang soạn tin</span>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                aria-hidden="true"
                style={{ animationDelay: `${i * 150}ms` }}
                className="size-2 rounded-full bg-muted-foreground/70 motion-safe:animate-bounce"
              />
            ))}
          </BubbleContent>
        </Bubble>
      </MessageContent>
    </Message>
  )
}
