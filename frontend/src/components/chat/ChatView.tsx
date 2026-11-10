import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react"
import { toast } from "sonner"
import { useChat } from "@/hooks/useChat"
import { useMeta } from "@/hooks/useMeta"
import { useSession } from "@/hooks/useSession"
import type { Rating } from "@/lib/api"
import { emotionMeta } from "@/lib/emotion-meta"
import type { Goal } from "@/lib/goals"
import { ChatHeader, type Connection } from "./ChatHeader"
import { EmptyState } from "./EmptyState"
import { MessageList } from "./MessageList"
import { PromptBar } from "./PromptBar"

export function ChatView() {
  const { sessionId, newSession } = useSession()
  const [goal, setGoal] = useState<Goal | null>(null)
  const {
    messages,
    pending,
    lastMeta,
    send,
    sendVoice,
    retry,
    rate,
    resetMeta,
  } = useChat(sessionId, goal)
  const { meta, failed, modelServer } = useMeta()

  const connection: Connection = failed
    ? "offline"
    : meta
      ? "online"
      : "connecting"
  const degraded = lastMeta?.degraded === true
  const warnedRef = useRef(false)

  useEffect(() => {
    if (degraded && !warnedRef.current) {
      warnedRef.current = true
      toast.warning("Hệ thống đang chạy ở chế độ dự phòng", {
        description: (lastMeta?.warnings ?? []).join("; ") || undefined,
      })
    }
  }, [degraded, lastMeta])

  const handleNew = () => {
    resetMeta()
    newSession()
  }

  const handleRate = async (id: string, rating: Rating) => {
    const ok = await rate(id, rating)
    if (!ok) toast.error("Chưa gửi được đánh giá. Bạn thử lại sau nhé.")
  }

  const showEmpty = messages.length === 0 && !pending

  // Màu nền aurora theo cảm xúc của tin gần nhất; chưa có thì giữ màu chủ đạo.
  const moodStyle = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]
      if (m.role === "user" && m.emotion) {
        return {
          "--mood": `var(${emotionMeta(m.emotion.label).cssVar})`,
        } as CSSProperties
      }
    }
    return undefined
  }, [messages])

  return (
    <div
      className="relative isolate h-dvh overflow-hidden bg-background"
      style={moodStyle}
    >
      <div className="aurora -z-10" aria-hidden="true" />
      <div className="mx-auto flex h-full max-w-3xl flex-col">
        <ChatHeader
          connection={connection}
          mode={lastMeta?.model_mode ?? meta?.model_mode}
          degraded={degraded}
          warnings={lastMeta?.warnings}
          modelServer={modelServer}
          llmBackend={lastMeta?.llm_backend}
          onNewConversation={handleNew}
        />
        {showEmpty ? (
          <EmptyState onPick={(text) => send(text)} />
        ) : (
          <MessageList
            messages={messages}
            pending={pending}
            onRetry={retry}
            onRate={handleRate}
          />
        )}
        <PromptBar
          onSend={send}
          onSendVoice={sendVoice}
          busy={pending}
          goal={goal}
          onGoalChange={setGoal}
        />
      </div>
    </div>
  )
}
