/** Mọi truy cập localStorage đều bọc try/catch: trang vẫn chạy khi bị chặn lưu trữ. */

export const SESSION_KEY = "ec.session_id"
export const messagesKey = (sessionId: string) => `ec.messages.${sessionId}`

export function readItem(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

export function writeItem(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    /* bị chặn hoặc đầy: bỏ qua */
  }
}

export function removeItem(key: string): void {
  try {
    window.localStorage.removeItem(key)
  } catch {
    /* bỏ qua */
  }
}

export function readJson<T>(key: string): T | null {
  const raw = readItem(key)
  if (raw === null) return null
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

export function writeJson(key: string, value: unknown): void {
  try {
    writeItem(key, JSON.stringify(value))
  } catch {
    /* bỏ qua */
  }
}
