import { useCallback, useEffect, useRef, useState } from "react"

/** Phần tối thiểu của Web Speech API mà ta dùng (TypeScript chưa có kiểu sẵn). */
interface RecognitionAlternative {
  transcript: string
}
interface RecognitionResult {
  isFinal: boolean
  0: RecognitionAlternative
}
interface RecognitionEvent {
  resultIndex: number
  results: { length: number; [index: number]: RecognitionResult }
}
interface Recognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((e: RecognitionEvent) => void) | null
  onerror: ((e: { error?: string }) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
  abort(): void
}
type RecognitionCtor = new () => Recognition

export function getRecognitionCtor(): RecognitionCtor | null {
  if (typeof window === "undefined") return null
  const w = window as unknown as {
    SpeechRecognition?: RecognitionCtor
    webkitSpeechRecognition?: RecognitionCtor
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

const join = (...parts: string[]) =>
  parts
    .map((p) => p.trim())
    .filter(Boolean)
    .join(" ")

// Lỗi khiến việc thử lại vô ích: dừng hẳn thay vì lặp.
const FATAL_ERRORS = new Set([
  "not-allowed",
  "service-not-allowed",
  "language-not-supported",
])

/**
 * Nhận dạng giọng nói trên trình duyệt (vi-VN) chạy song song lúc ghi âm, chỉ để dự phòng.
 * Mọi lỗi đều bị nuốt: trình duyệt không hỗ trợ thì mọi hàm là no-op.
 */
export function useSpeechFallback() {
  const supported = getRecognitionCtor() !== null
  const [text, setText] = useState("")
  const recRef = useRef<Recognition | null>(null)
  const activeRef = useRef(false)
  const finalRef = useRef("")
  const textRef = useRef("")

  const publish = useCallback((value: string) => {
    textRef.current = value
    setText(value)
  }, [])

  const stop = useCallback((): string => {
    activeRef.current = false
    const rec = recRef.current
    recRef.current = null
    if (rec) {
      rec.onresult = null
      rec.onerror = null
      rec.onend = null
      try {
        rec.stop()
      } catch {
        /* chưa chạy hoặc đã dừng */
      }
    }
    return textRef.current.trim()
  }, [])

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor()
    stop()
    finalRef.current = ""
    publish("")
    if (!Ctor) return
    try {
      const rec = new Ctor()
      rec.lang = "vi-VN"
      rec.continuous = true
      rec.interimResults = true
      rec.onresult = (e) => {
        let interim = ""
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const result = e.results[i]
          const piece = result[0]?.transcript ?? ""
          if (result.isFinal) finalRef.current = join(finalRef.current, piece)
          else interim = join(interim, piece)
        }
        publish(join(finalRef.current, interim))
      }
      rec.onerror = (e) => {
        if (e.error && FATAL_ERRORS.has(e.error)) activeRef.current = false
      }
      rec.onend = () => {
        // Chrome tự kết thúc sau một khoảng lặng: nối lại cho tới khi người dùng dừng ghi.
        if (!activeRef.current) return
        try {
          rec.start()
        } catch {
          activeRef.current = false
        }
      }
      activeRef.current = true
      recRef.current = rec
      rec.start()
    } catch {
      activeRef.current = false
      recRef.current = null
    }
  }, [publish, stop])

  const reset = useCallback(() => {
    finalRef.current = ""
    publish("")
  }, [publish])

  useEffect(() => () => void stop(), [stop])

  return { supported, text, start, stop, reset }
}
