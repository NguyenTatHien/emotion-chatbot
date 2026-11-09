import { vi } from "vitest"

/** MediaRecorder + getUserMedia giả cho jsdom (không có micro thật). */

export interface FakeMedia {
  getUserMedia: ReturnType<typeof vi.fn>
  trackStop: ReturnType<typeof vi.fn>
  recorders: FakeMediaRecorder[]
  /** Giả lập thời gian trôi qua cho performance.now(). */
  advanceClock: (ms: number) => void
  restore: () => void
}

export class FakeMediaRecorder {
  static supported: string[] = ["audio/webm;codecs=opus"]
  static isTypeSupported = (type: string) =>
    FakeMediaRecorder.supported.includes(type)
  static instances: FakeMediaRecorder[] = []

  mimeType: string
  state: "inactive" | "recording" = "inactive"
  timeslice: number | undefined
  ondataavailable: ((e: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  onerror: (() => void) | null = null

  stream: MediaStream

  constructor(stream: MediaStream, options?: { mimeType?: string }) {
    this.stream = stream
    this.mimeType = options?.mimeType ?? ""
    FakeMediaRecorder.instances.push(this)
  }

  start(timeslice?: number) {
    this.state = "recording"
    this.timeslice = timeslice
  }

  stop() {
    if (this.state === "inactive") return
    this.state = "inactive"
    this.ondataavailable?.({
      data: new Blob(["giả lập audio"], { type: this.mimeType }),
    })
    this.onstop?.()
  }
}

export function installFakeMedia(
  opts: { supported?: string[]; getUserMediaError?: string } = {}
): FakeMedia {
  FakeMediaRecorder.supported = opts.supported ?? ["audio/webm;codecs=opus"]
  FakeMediaRecorder.instances = []

  const trackStop = vi.fn()
  const stream = {
    getTracks: () => [{ stop: trackStop }],
  } as unknown as MediaStream
  const getUserMedia = vi.fn(async () => {
    if (opts.getUserMediaError) {
      throw new DOMException("từ chối", opts.getUserMediaError)
    }
    return stream
  })

  vi.stubGlobal("MediaRecorder", FakeMediaRecorder)
  Object.defineProperty(navigator, "mediaDevices", {
    value: { getUserMedia },
    configurable: true,
  })

  let now = 1000
  const nowSpy = vi.spyOn(performance, "now").mockImplementation(() => now)

  return {
    getUserMedia,
    trackStop,
    recorders: FakeMediaRecorder.instances,
    advanceClock: (ms) => {
      now += ms
    },
    restore: () => {
      nowSpy.mockRestore()
      vi.unstubAllGlobals()
      Reflect.deleteProperty(navigator, "mediaDevices")
    },
  }
}

/** SpeechRecognition giả: test tự bắn kết quả bằng `emit`. */
export class FakeRecognition {
  static instances: FakeRecognition[] = []
  lang = ""
  continuous = false
  interimResults = false
  started = 0
  stopped = false
  onresult: ((e: unknown) => void) | null = null
  onerror: ((e: { error?: string }) => void) | null = null
  onend: (() => void) | null = null

  constructor() {
    FakeRecognition.instances.push(this)
  }
  start() {
    this.started += 1
  }
  stop() {
    this.stopped = true
  }
  abort() {
    this.stopped = true
  }
  /** parts: danh sách [chữ, isFinal] của toàn bộ results tính từ resultIndex. */
  emit(parts: [string, boolean][], resultIndex = 0) {
    const results = parts.map(([transcript, isFinal]) => ({
      isFinal,
      0: { transcript },
    }))
    this.onresult?.({
      resultIndex,
      results: Object.assign(results, { length: results.length }),
    })
  }
}

export function installFakeSpeech() {
  FakeRecognition.instances = []
  vi.stubGlobal("webkitSpeechRecognition", FakeRecognition)
  return FakeRecognition.instances
}
