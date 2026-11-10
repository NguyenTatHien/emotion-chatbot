import type { CSSProperties } from "react"
import { ArrowUpRight, MessageCircleHeart } from "lucide-react"
import { emotionMeta, type EmotionLabel } from "@/lib/emotion-meta"

export const SUGGESTIONS = [
  "Hôm nay mình thấy mệt quá",
  "Mình vừa được điểm cao nên vui lắm",
  "Dạo này mình lo lắng và khó ngủ",
] as const

/** Màu và icon gợi ý cho từng câu mẫu (chỉ để trang trí). */
const SUGGESTION_MOOD: Record<(typeof SUGGESTIONS)[number], EmotionLabel> = {
  "Hôm nay mình thấy mệt quá": "Sadness",
  "Mình vừa được điểm cao nên vui lắm": "Enjoyment",
  "Dạo này mình lo lắng và khó ngủ": "Fear",
}

export function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="scroll-soft flex flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-8">
      <div className="flex w-full max-w-3xl flex-col items-center text-center">
        <div className="relative mb-6" aria-hidden="true">
          <div className="absolute inset-0 rounded-3xl bg-primary/40 blur-2xl" />
          <div className="relative flex size-16 items-center justify-center rounded-3xl bg-linear-to-br from-(--user-bubble-from) to-(--user-bubble-to) text-white shadow-lg shadow-primary/30">
            <MessageCircleHeart className="size-8" />
          </div>
        </div>
        <h2 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl lg:text-4xl">
          Chào bạn,{" "}
          <span className="text-gradient">mình ở đây để lắng nghe</span>
        </h2>
        <p className="mt-3 max-w-xl text-base text-pretty text-muted-foreground lg:text-lg">
          Kể cho mình nghe hôm nay của bạn thế nào. Mình sẽ đoán cảm xúc và gợi
          ý vài bài hát hợp tâm trạng.
        </p>

        <p className="mt-8 mb-3 text-sm font-medium text-muted-foreground">
          Hoặc thử một gợi ý:
        </p>
        <ul className="grid w-full gap-2.5 sm:grid-cols-3 lg:gap-4">
          {SUGGESTIONS.map((s) => {
            const meta = emotionMeta(SUGGESTION_MOOD[s])
            const Icon = meta.icon
            return (
              <li key={s} className="flex">
                <button
                  type="button"
                  onClick={() => onPick(s)}
                  style={{ "--tone": `var(${meta.cssVar})` } as CSSProperties}
                  className="group flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-2xl border border-border/70 bg-card/70 p-3 text-left text-sm shadow-sm backdrop-blur transition-colors duration-200 outline-none hover:border-(--tone) hover:bg-card focus-visible:ring-3 focus-visible:ring-ring/50 sm:flex-col sm:items-start sm:p-4 lg:p-5"
                >
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[color-mix(in_oklch,var(--tone)_14%,transparent)] text-(--tone)">
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <span className="flex-1 text-base leading-snug text-foreground sm:text-sm">
                    {s}
                  </span>
                  <ArrowUpRight
                    className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-(--tone) sm:hidden"
                    aria-hidden="true"
                  />
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
