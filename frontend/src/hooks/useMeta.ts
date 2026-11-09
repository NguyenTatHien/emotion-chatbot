import { useEffect, useState } from "react"
import { getMeta, type MetaResponse } from "@/lib/api"

export function useMeta() {
  const [meta, setMeta] = useState<MetaResponse | null>(null)
  const [failed, setFailed] = useState(false)

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

  return { meta, failed }
}
