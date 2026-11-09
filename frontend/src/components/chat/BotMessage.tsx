import { Bubble, BubbleContent } from "@/components/ui/bubble"
import { Message, MessageAvatar, MessageContent } from "@/components/ui/message"
import { SongList } from "@/components/music/SongList"
import { SafetyAlert } from "@/components/system/SafetyAlert"
import type { BotMessage as BotMsg } from "@/hooks/chat-state"
import { useTypewriter } from "@/hooks/useTypewriter"
import type { Rating } from "@/lib/api"
import { BotAvatar } from "./BotAvatar"
import { FeedbackButtons } from "./FeedbackButtons"

interface BotMessageProps {
  message: BotMsg
  onRate?: (id: string, rating: Rating) => void
}

export function BotMessage({ message, onRate }: BotMessageProps) {
  const { text } = useTypewriter(message.text, message.fresh === true)
  return (
    <Message>
      <MessageAvatar>
        <BotAvatar />
      </MessageAvatar>
      <MessageContent>
        {message.safety ? (
          <SafetyAlert text={text} />
        ) : (
          <Bubble variant="ghost">
            <BubbleContent className="text-base whitespace-pre-wrap">
              {text}
            </BubbleContent>
          </Bubble>
        )}
        {!message.safety ? <SongList songs={message.songs} /> : null}
        {!message.safety && message.turnId && onRate ? (
          <FeedbackButtons
            rating={message.rating}
            onRate={(rating) => onRate(message.id, rating)}
          />
        ) : null}
      </MessageContent>
    </Message>
  )
}
