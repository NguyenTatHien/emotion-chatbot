import { TriangleAlert } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const MODE_VI: Record<string, string> = {
  mock: "Mô phỏng",
  local: "Cục bộ",
  remote: "Máy chủ mô hình",
}

interface StatusBadgeProps {
  mode?: string | null
  degraded?: boolean
  warnings?: string[]
}

export function StatusBadge({
  mode,
  degraded = false,
  warnings = [],
}: StatusBadgeProps) {
  if (degraded) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="Đang chạy chế độ dự phòng. Xem chi tiết"
            className="rounded-4xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <Badge
              variant="outline"
              className="h-7 gap-1 border-emo-enjoyment px-2.5 text-emo-enjoyment"
            >
              <TriangleAlert aria-hidden="true" />
              Dự phòng
            </Badge>
          </button>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="font-medium">Hệ thống đang chạy ở chế độ dự phòng</p>
          {warnings.length > 0 ? (
            <ul className="mt-1 list-disc pl-4">
              {warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
        </TooltipContent>
      </Tooltip>
    )
  }
  if (!mode) return null
  return (
    <Badge variant="secondary" className="h-7 px-2.5">
      {MODE_VI[mode] ?? mode}
    </Badge>
  )
}
