import { Bot } from "lucide-react"

export function BotAvatar() {
  return (
    <div
      className="flex size-8 items-center justify-center rounded-xl bg-linear-to-br from-(--user-bubble-from) to-(--user-bubble-to) text-white shadow-sm shadow-primary/20"
      aria-hidden="true"
    >
      <Bot className="size-4" />
    </div>
  )
}
