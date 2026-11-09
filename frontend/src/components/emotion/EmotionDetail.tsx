import type { CSSProperties } from "react"
import { Progress } from "@/components/ui/progress"
import type { Emotion } from "@/lib/api"
import { EMOTION_LABELS, emotionMeta, percent } from "@/lib/emotion-meta"

export function EmotionDetail({ emotion }: { emotion: Emotion }) {
  const rows = EMOTION_LABELS.map((label) => ({
    label,
    value: emotion.probs[label] ?? 0,
  })).sort((a, b) => b.value - a.value)

  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-2.5" aria-label="Xác suất từng cảm xúc">
        {rows.map(({ label, value }) => {
          const meta = emotionMeta(label)
          const Icon = meta.icon
          const pct = percent(value)
          return (
            <li key={label} className="flex items-center gap-2 text-sm">
              <Icon
                className="size-4 shrink-0"
                style={{ color: `var(${meta.cssVar})` }}
                aria-hidden="true"
              />
              <span className="w-24 shrink-0">{meta.vi}</span>
              <Progress
                value={pct}
                aria-label={`${meta.vi} ${pct}%`}
                style={{ "--bar": `var(${meta.cssVar})` } as CSSProperties}
                className="h-2 flex-1 [&>[data-slot=progress-indicator]]:bg-(--bar)"
              />
              <span className="w-10 shrink-0 text-right tabular-nums text-muted-foreground">
                {pct}%
              </span>
            </li>
          )
        })}
      </ul>
      <p className="text-xs text-muted-foreground">
        Kết quả máy đoán, có thể sai
      </p>
    </div>
  )
}
