import { useCallback, useEffect, useRef } from "react"
import { RecorderError, useRecorder, type RecordingResult } from "./useRecorder"
import { useSpeechFallback } from "./useSpeechFallback"

export interface VoiceRecording extends RecordingResult {
  /** Chữ do Web Speech API nhận dạng sẵn trên trình duyệt (có thể rỗng). */
  transcriptHint: string
}

/** Ghép MediaRecorder (bản ghi gửi lên server) với Web Speech (chữ dự phòng, hiện trực tiếp). */
export function useVoiceRecording(
  onComplete: (voice: VoiceRecording) => void,
  onError: (error: RecorderError) => void
) {
  const speech = useSpeechFallback()
  const onCompleteRef = useRef(onComplete)
  useEffect(() => {
    onCompleteRef.current = onComplete
  })
  const cancelledRef = useRef(false)

  const recorder = useRecorder({
    onAutoStop: (result) => {
      onCompleteRef.current({ ...result, transcriptHint: speech.stop() })
    },
  })
  const {
    start: startRecorder,
    stop: stopRecorder,
    cancel: cancelRecorder,
  } = recorder
  const { start: startSpeech, stop: stopSpeech } = speech

  const start = useCallback(async () => {
    cancelledRef.current = false
    try {
      await startRecorder()
    } catch (err) {
      onError(err instanceof RecorderError ? err : new RecorderError("failed"))
      return
    }
    if (!cancelledRef.current) startSpeech()
  }, [onError, startRecorder, startSpeech])

  const send = useCallback(async () => {
    const result = await stopRecorder()
    const transcriptHint = stopSpeech()
    if (result) onCompleteRef.current({ ...result, transcriptHint })
  }, [stopRecorder, stopSpeech])

  const cancel = useCallback(() => {
    cancelledRef.current = true
    cancelRecorder()
    stopSpeech()
  }, [cancelRecorder, stopSpeech])

  return {
    state: recorder.state,
    active: recorder.state !== "idle",
    recording: recorder.state === "recording" || recorder.state === "stopping",
    elapsedMs: recorder.elapsedMs,
    maxMs: recorder.maxMs,
    liveText: speech.text,
    start,
    send,
    cancel,
  }
}
