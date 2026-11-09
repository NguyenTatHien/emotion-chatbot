import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { useChat } from "@/hooks/useChat"
import { useMeta } from "@/hooks/useMeta"
import { useSession } from "@/hooks/useSession"
import type { Goal } from "@/lib/goals"
import { ChatHeader, type Connection } from "./ChatHeader"
import { EmptyState } from "./EmptyState"
import { MessageList } from "./MessageList"
import { PromptBar } from "./PromptBar"

export function ChatView() {
  const { sessionId, newSession } = useSession()
  const [goal, setGoal] = useState<Goal | null>(null)
  const { messages, pending, lastMeta, send, retry, resetMeta } = useChat(
    sessionId,
    goal
  )
  const { meta, failed } = useMeta()

  const connection: Connection = failed ? "offline" : meta ? "online" : "connecting"
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

  const showEmpty = messages.length === 0 && !pending

  return (
    <div className="mx-auto flex h-dvh max-w-3xl flex-col bg-background">
      <ChatHeader
        connection={connection}
        mode={lastMeta?.model_mode ?? meta?.model_mode}
        degraded={degraded}
        warnings={lastMeta?.warnings}
        onNewConversation={handleNew}
      />
      {showEmpty ? (
        <EmptyState onPick={(text) => send(text)} />
      ) : (
        <MessageList messages={messages} pending={pending} onRetry={retry} />
      )}
      <PromptBar onSend={send} goal={goal} onGoalChange={setGoal} />
    </div>
  )
}
