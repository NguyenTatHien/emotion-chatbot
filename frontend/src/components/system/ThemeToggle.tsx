import { Check, Monitor, Moon, Sun, type LucideIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useTheme } from "@/components/theme-provider"

type Theme = "light" | "dark" | "system"

const OPTIONS: { value: Theme; label: string; icon: LucideIcon }[] = [
  { value: "light", label: "Sáng", icon: Sun },
  { value: "dark", label: "Tối", icon: Moon },
  { value: "system", label: "Theo hệ thống", icon: Monitor },
]

const CURRENT_VI: Record<Theme, string> = {
  light: "sáng",
  dark: "tối",
  system: "theo hệ thống",
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          className="relative size-11 shrink-0 rounded-full"
          aria-label={`Giao diện: ${CURRENT_VI[theme]}. Đổi giao diện`}
        >
          <Sun
            className="size-5 rotate-0 scale-100 transition-transform duration-300 dark:-rotate-90 dark:scale-0"
            aria-hidden="true"
          />
          <Moon
            className="absolute size-5 rotate-90 scale-0 transition-transform duration-300 dark:rotate-0 dark:scale-100"
            aria-hidden="true"
          />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Giao diện
        </DropdownMenuLabel>
        {OPTIONS.map(({ value, label, icon: Icon }) => (
          <DropdownMenuItem
            key={value}
            onSelect={() => setTheme(value)}
            aria-checked={theme === value}
            role="menuitemradio"
            className="min-h-10 cursor-pointer gap-2"
          >
            <Icon className="size-4" aria-hidden="true" />
            <span className="flex-1">{label}</span>
            {theme === value ? (
              <Check className="size-4 text-primary" aria-hidden="true" />
            ) : null}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
