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
  const fresh = message.fresh === true
  const { text, done } = useTypewriter(message.text, fresh)
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
            <BubbleContent className="max-w-[72ch] text-base leading-relaxed whitespace-pre-wrap lg:text-[17px]">
              {text}
            </BubbleContent>
          </Bubble>
        )}
        {/* Tin vừa nhận: chữ gõ xong mới hiện bài hát và nút đánh giá (trượt vào lần lượt). */}
        {!message.safety && done ? (
          <SongList songs={message.songs} animate={fresh} />
        ) : null}
        {!message.safety && done && message.turnId && onRate ? (
          <FeedbackButtons
            rating={message.rating}
            onRate={(rating) => onRate(message.id, rating)}
          />
        ) : null}
      </MessageContent>
    </Message>
  )
}
