import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react"
import { toast } from "sonner"
import { useChat } from "@/hooks/useChat"
import { useMeta } from "@/hooks/useMeta"
import { useSession } from "@/hooks/useSession"
import type { ChatMessage } from "@/hooks/chat-state"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import type { Rating } from "@/lib/api"
import { emotionMeta } from "@/lib/emotion-meta"
import type { Goal } from "@/lib/goals"
import { AppSidebar } from "./AppSidebar"
import { ChatHeader, type Connection } from "./ChatHeader"
import { EmptyState } from "./EmptyState"
import { MessageList } from "./MessageList"
import { PromptBar } from "./PromptBar"

const TITLE_MAX = 60

/** Tiêu đề cuộc trò chuyện = tin đầu tiên của người dùng. */
export function conversationTitle(messages: ChatMessage[]): string {
  const first = messages.find((m) => m.role === "user")
  if (!first) return "Cuộc trò chuyện mới"
  const text = first.text.trim().replace(/\s+/g, " ")
  if (!text)
    return first.role === "user" && first.kind === "voice"
      ? "Tin nhắn giọng nói"
      : "Cuộc trò chuyện mới"
  return text.length > TITLE_MAX ? `${text.slice(0, TITLE_MAX - 1)}…` : text
}

/** Trạng thái mở sidebar lần trước (component sidebar lưu vào cookie). */
function sidebarDefaultOpen(): boolean {
  try {
    return !document.cookie.split("; ").includes("sidebar_state=false")
  } catch {
    return true
  }
}

export function ChatView() {
  const {
    sessionId,
    newSession,
    conversations,
    selectSession,
    recordConversation,
    deleteConversation,
  } = useSession()
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

  const handleSelect = (id: string) => {
    if (id === sessionId) return
    resetMeta()
    selectSession(id)
  }

  const handleDelete = (id: string) => {
    if (id === sessionId) resetMeta()
    deleteConversation(id)
  }

  const title = conversationTitle(messages)
  const lastAt = messages.at(-1)?.createdAt

  // Có tin thì đưa cuộc này lên đầu lịch sử ở sidebar.
  useEffect(() => {
    if (!lastAt) return
    recordConversation({ id: sessionId, title, updatedAt: lastAt })
  }, [sessionId, title, lastAt, recordConversation])

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
    <SidebarProvider defaultOpen={sidebarDefaultOpen()} style={moodStyle}>
      <AppSidebar
        conversations={conversations}
        activeId={sessionId}
        onNew={handleNew}
        onSelect={handleSelect}
        onDelete={handleDelete}
      />
      <SidebarInset className="relative isolate h-dvh min-w-0 overflow-hidden">
        <div className="aurora -z-10" aria-hidden="true" />
        <ChatHeader
          title={messages.length > 0 ? title : undefined}
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
      </SidebarInset>
    </SidebarProvider>
  )
}
