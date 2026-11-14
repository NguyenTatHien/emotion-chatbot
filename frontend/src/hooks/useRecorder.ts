import { useCallback, useEffect, useRef, useState } from "react"

export const MAX_RECORDING_MS = 30_000
export const TIMESLICE_MS = 250

/** Thứ tự ưu tiên; Safari chỉ có audio/mp4, Chrome/Edge/Firefox có webm hoặc ogg opus. */
export const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/ogg;codecs=opus",
  "audio/mp4",
] as const

export type RecorderState = "idle" | "requesting" | "recording" | "stopping"
export type RecorderErrorKind =
  "denied" | "no-device" | "unsupported" | "insecure" | "failed"

export interface RecordingResult {
  blob: Blob
  mimeType: string
  durationMs: number
}

export class RecorderError extends Error {
  kind: RecorderErrorKind
  constructor(kind: RecorderErrorKind) {
    super(recorderErrorMessage(kind))
    this.name = "RecorderError"
    this.kind = kind
  }
}

export function recorderErrorMessage(kind: RecorderErrorKind): string {
  switch (kind) {
    case "denied":
      return "Bạn đã chặn quyền micro. Hãy bấm biểu tượng ổ khoá trên thanh địa chỉ, cho phép micro rồi thử lại. Bạn vẫn có thể gõ chữ."
    case "no-device":
      return "Không tìm thấy micro. Hãy cắm micro rồi thử lại, hoặc gõ chữ để trò chuyện."
    case "unsupported":
      return "Trình duyệt này chưa hỗ trợ ghi âm. Hãy dùng Chrome, Edge, Firefox hoặc Safari mới, hoặc gõ chữ."
    case "insecure":
      return "Ghi âm chỉ hoạt động trên localhost hoặc HTTPS. Hãy mở trang bằng địa chỉ an toàn, hoặc gõ chữ."
    default:
      return "Không bắt đầu ghi âm được. Hãy thử lại hoặc gõ chữ để trò chuyện."
  }
}

/** Chọn mimeType đầu tiên trình duyệt hỗ trợ; "" nghĩa là dùng mặc định của trình duyệt. */
export function pickMimeType(): string {
  if (
    typeof MediaRecorder === "undefined" ||
    typeof MediaRecorder.isTypeSupported !== "function"
  ) {
    return ""
  }
  return (
    MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) ?? ""
  )
}

/** Tên file gửi lên theo mimeType (backend vẫn dò theo nội dung, tên chỉ để dễ đọc log). */
export function filenameFor(mimeType: string): string {
  const base = mimeType.split(";")[0].trim().toLowerCase()
  if (base === "audio/ogg") return "voice.ogg"
  if (base === "audio/mp4" || base === "audio/aac" || base === "audio/x-m4a")
    return "voice.m4a"
  if (base === "audio/wav" || base === "audio/x-wav") return "voice.wav"
  return "voice.webm"
}

/** 0:07, 1:05 */
export function formatClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

function classifyError(err: unknown): RecorderError {
  const name =
    err instanceof DOMException || err instanceof Error ? err.name : ""
  if (
    name === "NotAllowedError" ||
    name === "SecurityError" ||
    name === "PermissionDeniedError"
  ) {
    return new RecorderError("denied")
  }
  if (
    name === "NotFoundError" ||
    name === "DevicesNotFoundError" ||
    name === "OverconstrainedError"
  ) {
    return new RecorderError("no-device")
  }
  return new RecorderError("failed")
}

function checkSupport(): void {
  if (typeof window !== "undefined" && window.isSecureContext === false) {
    throw new RecorderError("insecure")
  }
  if (
    typeof MediaRecorder === "undefined" ||
    typeof navigator === "undefined" ||
    !navigator.mediaDevices ||
    typeof navigator.mediaDevices.getUserMedia !== "function"
  ) {
    throw new RecorderError("unsupported")
  }
}

interface UseRecorderOptions {
  maxMs?: number
  /** Gọi khi ghi đủ `maxMs` và tự dừng. */
  onAutoStop?: (result: RecordingResult) => void
}

export function useRecorder({
  maxMs = MAX_RECORDING_MS,
  onAutoStop,
}: UseRecorderOptions = {}) {
  const [state, setStateRaw] = useState<RecorderState>("idle")
  const [elapsedMs, setElapsedMs] = useState(0)

  const stateRef = useRef<RecorderState>("idle")
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startedAtRef = useRef(0)
  const mimeRef = useRef("")
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const limitRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cancelledRef = useRef(false)
  const onAutoStopRef = useRef(onAutoStop)
  useEffect(() => {
    onAutoStopRef.current = onAutoStop
  })

  const setState = useCallback((next: RecorderState) => {
    stateRef.current = next
    setStateRaw(next)
  }, [])

  const clearTimers = useCallback(() => {
    if (tickRef.current !== null) clearInterval(tickRef.current)
    if (limitRef.current !== null) clearTimeout(limitRef.current)
    tickRef.current = null
    limitRef.current = null
  }, [])

  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const finish = useCallback(
    (forcedDurationMs?: number): Promise<RecordingResult | null> => {
      const recorder = recorderRef.current
      if (stateRef.current !== "recording" || !recorder)
        return Promise.resolve(null)
      setState("stopping")
      clearTimers()
      const durationMs =
        forcedDurationMs ??
        Math.min(performance.now() - startedAtRef.current, maxMs)
      return new Promise((resolve) => {
        recorder.onstop = () => {
          const mimeType = recorder.mimeType || mimeRef.current || "audio/webm"
          const blob = new Blob(chunksRef.current, { type: mimeType })
          chunksRef.current = []
          recorderRef.current = null
          releaseStream()
          setState("idle")
          setElapsedMs(0)
          resolve({ blob, mimeType, durationMs: Math.round(durationMs) })
        }
        try {
          recorder.stop()
        } catch {
          recorderRef.current = null
          releaseStream()
          setState("idle")
          resolve(null)
        }
      })
    },
    [clearTimers, maxMs, releaseStream, setState]
  )

  const cancel = useCallback(() => {
    cancelledRef.current = true
    clearTimers()
    const recorder = recorderRef.current
    if (recorder) {
      recorder.ondataavailable = null
      recorder.onstop = null
      recorder.onerror = null
      try {
        if (recorder.state !== "inactive") recorder.stop()
      } catch {
        /* đã dừng */
      }
    }
    recorderRef.current = null
    chunksRef.current = []
    releaseStream()
    setElapsedMs(0)
    setState("idle")
  }, [clearTimers, releaseStream, setState])

  const start = useCallback(async (): Promise<void> => {
    if (stateRef.current !== "idle") return
    checkSupport()
    cancelledRef.current = false
    setState("requesting")

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        // Tắt tự cân âm lượng (AGC): giữ độ to thật của giọng để đo mức kích động
        // (nói to ra to, thì thầm ra nhỏ). Bật AGC thì mọi giọng bị kéo về "vừa".
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
        },
      })
    } catch (err) {
      setState("idle")
      throw classifyError(err)
    }
    if (cancelledRef.current) {
      // Người dùng huỷ trong lúc trình duyệt còn hỏi quyền.
      stream.getTracks().forEach((track) => track.stop())
      return
    }

    let recorder: MediaRecorder
    const mimeType = pickMimeType()
    try {
      recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)
    } catch {
      stream.getTracks().forEach((track) => track.stop())
      setState("idle")
      throw new RecorderError("unsupported")
    }
    streamRef.current = stream
    recorderRef.current = recorder
    mimeRef.current = mimeType
    chunksRef.current = []
    recorder.ondataavailable = (e: BlobEvent) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.onerror = () => cancel()

    recorder.start(TIMESLICE_MS)
    startedAtRef.current = performance.now()
    setElapsedMs(0)
    setState("recording")
    tickRef.current = setInterval(() => {
      setElapsedMs(Math.min(performance.now() - startedAtRef.current, maxMs))
    }, 100)
    limitRef.current = setTimeout(() => {
      void finish(maxMs).then((result) => {
        if (result) onAutoStopRef.current?.(result)
      })
    }, maxMs)
  }, [cancel, finish, maxMs, setState])

  const stop = useCallback(() => finish(), [finish])

  // Rời trang: luôn trả micro lại cho hệ thống.
  useEffect(() => cancel, [cancel])

  return { state, elapsedMs, maxMs, start, stop, cancel }
}
