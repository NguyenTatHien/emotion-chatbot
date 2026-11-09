import { Bot, MessageSquarePlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/system/StatusBadge"

export const BOT_NAME = "Bạn đồng hành"

export type Connection = "connecting" | "online" | "offline"

const STATUS_TEXT: Record<Connection, string> = {
  connecting: "Đang kết nối…",
  online: "Đang hoạt động",
  offline: "Chưa kết nối được máy chủ",
}

interface ChatHeaderProps {
  connection: Connection
  mode?: string | null
  degraded?: boolean
  warnings?: string[]
  onNewConversation: () => void
}

export function ChatHeader({
  connection,
  mode,
  degraded,
  warnings,
  onNewConversation,
}: ChatHeaderProps) {
  return (
    <header className="flex items-center gap-3 border-b px-4 py-2">
      <div
        className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
        aria-hidden="true"
      >
        <Bot className="size-5" />
      </div>
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-base font-semibold leading-tight">
          {BOT_NAME}
        </h1>
        <p
          className="flex items-center gap-1.5 text-sm text-muted-foreground"
          role="status"
        >
          <span
            aria-hidden="true"
            className={
              connection === "online"
                ? "size-2 rounded-full bg-emo-fear"
                : connection === "offline"
                  ? "size-2 rounded-full bg-destructive"
                  : "size-2 rounded-full bg-muted-foreground"
            }
          />
          {STATUS_TEXT[connection]}
        </p>
      </div>
      <StatusBadge mode={mode} degraded={degraded} warnings={warnings} />
      <Button
        type="button"
        variant="ghost"
        className="size-11 shrink-0 sm:w-auto sm:px-3"
        aria-label="Cuộc trò chuyện mới"
        onClick={onNewConversation}
      >
        <MessageSquarePlus className="size-5" aria-hidden="true" />
        <span className="hidden sm:inline">Cuộc trò chuyện mới</span>
      </Button>
    </header>
  )
}
