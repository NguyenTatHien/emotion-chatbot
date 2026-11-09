import { Server, ServerOff, TriangleAlert } from "lucide-react"
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

const LLM_VI: Record<string, string> = {
  mock: "Mô phỏng",
  qwen: "Qwen",
  gemini: "Gemini",
  canned: "Câu soạn sẵn",
}

interface StatusBadgeProps {
  mode?: string | null
  degraded?: boolean
  warnings?: string[]
  /** Trạng thái model server từ /api/health; null khi chưa biết. */
  modelServer?: "up" | "down" | "n/a" | null
  /** Nguồn thực tế đã trả lời ở lượt gần nhất. */
  llmBackend?: string | null
}

function ModelServerBadge({ status }: { status: "up" | "down" }) {
  const down = status === "down"
  return (
    <Badge
      variant="outline"
      className={
        down
          ? "h-7 gap-1 border-destructive px-2.5 text-destructive"
          : "h-7 gap-1 px-2.5"
      }
      role="status"
      aria-label={
        down ? "Máy chủ mô hình đang ngắt kết nối" : "Máy chủ mô hình hoạt động"
      }
    >
      {down ? (
        <ServerOff aria-hidden="true" />
      ) : (
        <Server aria-hidden="true" />
      )}
      <span className="hidden sm:inline">
        {down ? "Máy chủ mô hình ngắt" : "Máy chủ mô hình"}
      </span>
    </Badge>
  )
}

export function StatusBadge({
  mode,
  degraded = false,
  warnings = [],
  modelServer = null,
  llmBackend = null,
}: StatusBadgeProps) {
  return (
    <div className="flex items-center gap-1.5">
      {modelServer === "up" || modelServer === "down" ? (
        <ModelServerBadge status={modelServer} />
      ) : null}
      {llmBackend ? (
        <Badge
          variant="outline"
          className="hidden h-7 px-2.5 sm:inline-flex"
          aria-label={`Nguồn trả lời gần nhất: ${LLM_VI[llmBackend] ?? llmBackend}`}
        >
          {LLM_VI[llmBackend] ?? llmBackend}
        </Badge>
      ) : null}
      <ModeBadge mode={mode} degraded={degraded} warnings={warnings} />
    </div>
  )
}

function ModeBadge({
  mode,
  degraded,
  warnings,
}: {
  mode?: string | null
  degraded: boolean
  warnings: string[]
}) {
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
