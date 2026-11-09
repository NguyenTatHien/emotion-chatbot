import { ThumbsDown, ThumbsUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Rating } from "@/lib/api"

interface FeedbackButtonsProps {
  rating: Rating | null | undefined
  onRate: (rating: Rating) => void
}

const OPTIONS: { value: Rating; label: string; Icon: typeof ThumbsUp }[] = [
  { value: "up", label: "Hữu ích", Icon: ThumbsUp },
  { value: "down", label: "Chưa hợp", Icon: ThumbsDown },
]

export function FeedbackButtons({ rating, onRate }: FeedbackButtonsProps) {
  return (
    <div
      role="group"
      aria-label="Đánh giá câu trả lời"
      className="flex items-center gap-1"
    >
      {OPTIONS.map(({ value, label, Icon }) => {
        const pressed = rating === value
        return (
          <Button
            key={value}
            type="button"
            variant={pressed ? "secondary" : "ghost"}
            className="size-11 text-muted-foreground aria-pressed:text-primary"
            aria-label={label}
            aria-pressed={pressed}
            onClick={() => onRate(value)}
          >
            <Icon
              className="size-4"
              aria-hidden="true"
              fill={pressed ? "currentColor" : "none"}
            />
          </Button>
        )
      })}
    </div>
  )
}
