import { Mic } from "lucide-react"
import { Button } from "@/components/ui/button"

interface RecordButtonProps {
  onClick: () => void
  disabled?: boolean
  /** Đang xin quyền micro. */
  busy?: boolean
}

export function RecordButton({ onClick, disabled, busy }: RecordButtonProps) {
  return (
    <Button
      type="button"
      variant="ghost"
      className="size-11 shrink-0 cursor-pointer rounded-full text-muted-foreground hover:bg-primary/10 hover:text-primary"
      aria-label="Ghi âm"
      aria-busy={busy || undefined}
      disabled={disabled || busy}
      onClick={onClick}
    >
      <Mic className="size-5" aria-hidden="true" />
    </Button>
  )
}
