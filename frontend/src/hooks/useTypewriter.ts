import { useEffect, useState } from "react"
import { usePrefersReducedMotion } from "./usePrefersReducedMotion"

export const TYPEWRITER_MAX_MS = 1500

/** Tách văn bản thành các cụm từ (giữ khoảng trắng đi kèm). */
export function splitChunks(text: string): string[] {
  return text.match(/\S+\s*|\s+/g) ?? []
}

/** Hiện dần theo cụm từ, tổng thời gian không vượt TYPEWRITER_MAX_MS. */
export function useTypewriter(text: string, enabled: boolean) {
  const reduced = usePrefersReducedMotion()
  const active = enabled && !reduced
  const [count, setCount] = useState(0)
  const chunks = splitChunks(text)
  const total = chunks.length

  useEffect(() => {
    if (!active || total === 0) return
    const step = Math.min(60, TYPEWRITER_MAX_MS / total)
    let n = 0
    const timer = window.setInterval(() => {
      n += 1
      setCount(n)
      if (n >= total) window.clearInterval(timer)
    }, step)
    return () => window.clearInterval(timer)
  }, [active, total, text])

  if (!active) return { text, done: true }
  const shown = Math.min(count, total)
  return { text: chunks.slice(0, shown).join(""), done: shown >= total }
}
