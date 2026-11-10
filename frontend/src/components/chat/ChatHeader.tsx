import { Bot, MessageSquarePlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/system/StatusBadge"
import { ThemeToggle } from "@/components/system/ThemeToggle"

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
  modelServer?: "up" | "down" | "n/a" | null
  llmBackend?: string | null
  onNewConversation: () => void
}

export function ChatHeader({
  connection,
  mode,
  degraded,
  warnings,
  modelServer,
  llmBackend,
  onNewConversation,
}: ChatHeaderProps) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-2 border-b border-border/60 bg-background/70 px-3 py-2 backdrop-blur-xl sm:gap-3 sm:px-4">
      <div className="relative shrink-0" aria-hidden="true">
        <div className="flex size-10 items-center justify-center rounded-2xl bg-linear-to-br from-(--user-bubble-from) to-(--user-bubble-to) text-white shadow-md shadow-primary/25">
          <Bot className="size-5" />
        </div>
        <span
          className={
            "absolute -right-0.5 -bottom-0.5 size-3 rounded-full border-2 border-background " +
            (connection === "online"
              ? "bg-emerald-500"
              : connection === "offline"
                ? "bg-destructive"
                : "bg-muted-foreground")
          }
        />
      </div>
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-base font-semibold leading-tight">
          {BOT_NAME}
        </h1>
        <p
          className="truncate text-sm text-muted-foreground"
          role="status"
        >
          {STATUS_TEXT[connection]}
        </p>
      </div>
      <StatusBadge
        mode={mode}
        degraded={degraded}
        warnings={warnings}
        modelServer={modelServer}
        llmBackend={llmBackend}
      />
      <ThemeToggle />
      <Button
        type="button"
        variant="ghost"
        className="size-11 shrink-0 rounded-full sm:w-auto sm:rounded-lg sm:px-3"
        aria-label="Cuộc trò chuyện mới"
        onClick={onNewConversation}
      >
        <MessageSquarePlus className="size-5" aria-hidden="true" />
        <span className="hidden sm:inline">Cuộc trò chuyện mới</span>
      </Button>
    </header>
  )
}
