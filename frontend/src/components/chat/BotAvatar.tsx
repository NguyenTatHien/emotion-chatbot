import { Bot } from "lucide-react"

export function BotAvatar() {
  return (
    <div
      className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-primary"
      aria-hidden="true"
    >
      <Bot className="size-4" />
    </div>
  )
}
