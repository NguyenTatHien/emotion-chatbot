import type { CSSProperties, ReactNode } from "react"
import { ChevronDown } from "lucide-react"
import { Progress } from "@/components/ui/progress"
import type { Analysis, Emotion } from "@/lib/api"
import {
  EMOTION_LABELS,
  emotionMeta,
  percent,
  type Arousal,
} from "@/lib/emotion-meta"

const TOP_LABELS = 3

const AROUSAL_LEVEL_VI: Record<Arousal, string> = {
  low: "thấp",
  medium: "vừa",
  high: "cao",
}

interface ReplyAnalysisProps {
  analysis: Analysis
  emotion?: Emotion | null
  /** Lượt có rủi ro an toàn: chỉ hiện mục An toàn và Nhạc. */
  safety?: boolean
  latencyMs?: number
}

/** "1,2" cho 1234 ms: một chữ số thập phân, dấu phẩy; dưới 0,1 giây thì ghi "dưới 0,1". */
function formatSeconds(latencyMs: number): string {
  if (latencyMs < 100) return "dưới 0,1"
  return (latencyMs / 1000).toFixed(1).replace(".", ",")
}

function emotionName(label: string): string {
  return label === "safety" ? "nội dung nhạy cảm" : emotionMeta(label).vi
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-1">
      <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {title}
      </h4>
      {children}
    </section>
  )
}

function EmotionBars({ emotion }: { emotion: Emotion }) {
  const rows = EMOTION_LABELS.map((label) => ({
    label,
    pct: percent(emotion.probs[label]),
  }))
    .sort((a, b) => b.pct - a.pct)
    .slice(0, TOP_LABELS)
  const other = Math.max(0, 100 - rows.reduce((sum, r) => sum + r.pct, 0))
  return (
    <ul className="flex flex-col gap-1.5" aria-label="Xác suất các cảm xúc chính">
      {rows.map(({ label, pct }) => {
        const meta = emotionMeta(label)
        const Icon = meta.icon
        return (
          <li key={label} className="flex items-center gap-2">
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
      {other > 0 ? (
        <li className="pl-6 text-muted-foreground">Khác {other}%</li>
      ) : null}
    </ul>
  )
}

function EmotionSection({
  analysis,
  emotion,
}: {
  analysis: Analysis
  emotion?: Emotion | null
}) {
  if (analysis.emotion_source === "fallback") {
    return <p>Mô hình cảm xúc tạm không khả dụng</p>
  }
  if (!emotion) return <p>Chưa có kết quả cảm xúc</p>
  return <EmotionBars emotion={emotion} />
}

function VoiceSection({ emotion }: { emotion: Emotion }) {
  if (!emotion.arousal) return null
  const fused =
    emotion.label_text && emotion.label_text !== emotion.label
      ? ` · theo lời nói: ${emotionMeta(emotion.label_text).vi} → kết hợp giọng: ${emotionMeta(emotion.label).vi}`
      : ""
  return (
    <Section title="Giọng nói">
      <p>
        Kích động {AROUSAL_LEVEL_VI[emotion.arousal]}
        {fused}
      </p>
    </Section>
  )
}

function ContextSection({ analysis }: { analysis: Analysis }) {
  const recent = analysis.recent_emotions ?? []
  return (
    <Section title="Ngữ cảnh">
      <ul className="flex flex-col gap-0.5">
        <li>Lượt thứ {analysis.turn}</li>
        {recent.length > 0 ? (
          <li>
            Cảm xúc các lượt gần đây:{" "}
            {recent.map((r) => `lượt ${r.turn} ${emotionName(r.label)}`).join("; ")}
          </li>
        ) : null}
        <li>
          {analysis.last_music_turn != null
            ? `Gợi ý nhạc gần nhất: lượt ${analysis.last_music_turn}`
            : "Chưa gợi ý nhạc lần nào"}
        </li>
      </ul>
    </Section>
  )
}

/** Khung thu gọn "Đã phân tích" phía trên câu trả lời: những gì bot đã dùng để trả lời. */
export function ReplyAnalysis({
  analysis,
  emotion,
  safety = false,
  latencyMs,
}: ReplyAnalysisProps) {
  const title =
    latencyMs != null
      ? `Đã phân tích · ${formatSeconds(latencyMs)} giây`
      : "Đã phân tích"
  return (
    <details
      data-slot="reply-analysis"
      className="group w-full max-w-[72ch] rounded-xl border bg-card/60 text-sm text-card-foreground"
    >
      <summary className="flex min-h-11 cursor-pointer list-none items-center gap-1.5 rounded-xl px-3 py-2 text-muted-foreground outline-none select-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 [&::-webkit-details-marker]:hidden">
        <ChevronDown
          className="size-4 transition-transform group-open:rotate-180 motion-reduce:transition-none"
          aria-hidden="true"
        />
        {title}
      </summary>
      <div className="flex flex-col gap-3 border-t px-3 py-3">
        <Section title="An toàn">
          <p>
            {safety
              ? "Phát hiện nội dung cần hỗ trợ"
              : "Không phát hiện rủi ro"}
          </p>
        </Section>
        {safety ? null : (
          <>
            <Section title="Cảm xúc">
              <EmotionSection analysis={analysis} emotion={emotion} />
            </Section>
            {emotion ? <VoiceSection emotion={emotion} /> : null}
            <ContextSection analysis={analysis} />
            {analysis.tone ? (
              <Section title="Cách trả lời">
                <p>{analysis.tone.text}</p>
              </Section>
            ) : null}
          </>
        )}
        <Section title="Nhạc">
          <p>{analysis.music_reason}</p>
        </Section>
      </div>
    </details>
  )
}
