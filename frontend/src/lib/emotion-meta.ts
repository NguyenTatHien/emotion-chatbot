import {
  Angry,
  Annoyed,
  Frown,
  Laugh,
  Meh,
  ShieldAlert,
  Sparkles,
  type LucideIcon,
} from "lucide-react"

export const EMOTION_LABELS = [
  "Anger",
  "Disgust",
  "Enjoyment",
  "Fear",
  "Other",
  "Sadness",
  "Surprise",
] as const

export type EmotionLabel = (typeof EMOTION_LABELS)[number]
export type Arousal = "low" | "medium" | "high"

export interface EmotionMeta {
  vi: string
  icon: LucideIcon
  /** Tên biến CSS (khai báo trong index.css) cho màu của nhãn. */
  cssVar: string
}

export const EMOTION_META: Record<EmotionLabel, EmotionMeta> = {
  Anger: { vi: "Tức giận", icon: Angry, cssVar: "--emo-anger" },
  Disgust: { vi: "Khó chịu", icon: Annoyed, cssVar: "--emo-disgust" },
  Enjoyment: { vi: "Vui vẻ", icon: Laugh, cssVar: "--emo-enjoyment" },
  Fear: { vi: "Lo sợ", icon: ShieldAlert, cssVar: "--emo-fear" },
  Other: { vi: "Bình thường", icon: Meh, cssVar: "--emo-other" },
  Sadness: { vi: "Buồn", icon: Frown, cssVar: "--emo-sadness" },
  Surprise: { vi: "Ngạc nhiên", icon: Sparkles, cssVar: "--emo-surprise" },
}

export function isEmotionLabel(value: string): value is EmotionLabel {
  return (EMOTION_LABELS as readonly string[]).includes(value)
}

/** Nhãn lạ (backend thêm nhãn mới) rơi về "Other". */
export function emotionMeta(label: string): EmotionMeta {
  return isEmotionLabel(label) ? EMOTION_META[label] : EMOTION_META.Other
}

export function percent(prob: number | undefined): number {
  return Math.round((prob ?? 0) * 100)
}
