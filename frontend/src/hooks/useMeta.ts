import { useEffect, useState } from "react"
import {
  getHealth,
  getMeta,
  type HealthResponse,
  type MetaResponse,
} from "@/lib/api"

export const HEALTH_POLL_MS = 30_000

export type ModelServerStatus = HealthResponse["model_server"]

export function useMeta() {
  const [meta, setMeta] = useState<MetaResponse | null>(null)
  const [failed, setFailed] = useState(false)
  const [modelServer, setModelServer] = useState<ModelServerStatus | null>(
    null
  )

  useEffect(() => {
    const controller = new AbortController()
    getMeta(controller.signal)
      .then((m) => {
        setMeta(m)
        setFailed(false)
      })
      .catch((err: unknown) => {
        if ((err as { name?: string })?.name !== "AbortError") setFailed(true)
      })
    return () => controller.abort()
  }, [])

  // Thăm /api/health mỗi 30 giây khi tab đang hiện; quay lại tab thì thăm ngay.
  useEffect(() => {
    const controller = new AbortController()
    const poll = () => {
      if (document.visibilityState === "hidden") return
      getHealth(controller.signal)
        .then((h) => setModelServer(h.model_server))
        .catch((err: unknown) => {
          if ((err as { name?: string })?.name !== "AbortError")
            setModelServer(null)
        })
    }
    poll()
    const timer = window.setInterval(poll, HEALTH_POLL_MS)
    document.addEventListener("visibilitychange", poll)
    return () => {
      controller.abort()
      window.clearInterval(timer)
      document.removeEventListener("visibilitychange", poll)
    }
  }, [])

  return { meta, failed, modelServer }
}
