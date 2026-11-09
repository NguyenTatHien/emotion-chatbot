import type { CSSProperties } from "react"
import { Activity } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import type { Emotion } from "@/lib/api"
import {
  AROUSAL_VI,
  emotionMeta,
  percent,
  type Arousal,
} from "@/lib/emotion-meta"
import { EmotionDetail } from "./EmotionDetail"

export function emotionStyle(cssVar: string): CSSProperties {
  return {
    color: `var(${cssVar})`,
    backgroundColor: `color-mix(in oklch, var(${cssVar}) 12%, transparent)`,
  }
}

export function EmotionChip({ emotion }: { emotion: Emotion }) {
  const meta = emotionMeta(emotion.label)
  const Icon = meta.icon
  const pct = percent(emotion.probs[emotion.label])
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Cảm xúc ${meta.vi} ${pct}%. Bấm để xem chi tiết`}
          style={emotionStyle(meta.cssVar)}
          className="inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-sm font-medium outline-none transition-colors hover:brightness-95 focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <Icon className="size-4" aria-hidden="true" />
          <span>
            {meta.vi} {pct}%
          </span>
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72">
        <EmotionDetail emotion={emotion} />
      </PopoverContent>
    </Popover>
  )
}

export function ArousalChip({ arousal }: { arousal: Arousal }) {
  return (
    <Badge
      variant="outline"
      className="h-8 gap-1.5 px-3 text-sm font-normal text-muted-foreground"
    >
      <Activity className="size-4" aria-hidden="true" />
      {AROUSAL_VI[arousal]}
    </Badge>
  )
}
