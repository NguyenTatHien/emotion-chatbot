import { MessageCircleHeart } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"

export const SUGGESTIONS = [
  "Hôm nay mình thấy mệt quá",
  "Mình vừa được điểm cao nên vui lắm",
  "Dạo này mình lo lắng và khó ngủ",
] as const

export function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <Empty className="flex-1">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <MessageCircleHeart aria-hidden="true" />
        </EmptyMedia>
        <EmptyTitle className="text-lg">
          Chào bạn, mình ở đây để lắng nghe
        </EmptyTitle>
        <EmptyDescription className="text-base">
          Kể cho mình nghe hôm nay của bạn thế nào. Mình sẽ đoán cảm xúc và gợi ý
          vài bài hát hợp tâm trạng.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent className="max-w-md">
        <p className="text-sm text-muted-foreground">Hoặc thử một gợi ý:</p>
        <div className="flex w-full flex-col gap-2">
          {SUGGESTIONS.map((s) => (
            <Button
              key={s}
              type="button"
              variant="outline"
              className="h-auto min-h-11 whitespace-normal px-4 py-2 text-base"
              onClick={() => onPick(s)}
            >
              {s}
            </Button>
          ))}
        </div>
      </EmptyContent>
    </Empty>
  )
}
