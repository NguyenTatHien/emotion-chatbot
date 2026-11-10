import { Bot, MessageSquare, MessageSquarePlus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"
import type { Conversation } from "@/hooks/useSession"
import { BOT_NAME } from "./ChatHeader"

interface AppSidebarProps {
  conversations: Conversation[]
  activeId: string
  onNew: () => void
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

const DAY = 24 * 60 * 60 * 1000

/** Nhóm theo thời gian như các app chat: Hôm nay, 7 ngày qua, Cũ hơn. */
export function groupConversations(
  list: Conversation[],
  now: Date = new Date()
): { label: string; items: Conversation[] }[] {
  const startOfToday = new Date(now)
  startOfToday.setHours(0, 0, 0, 0)
  const today: Conversation[] = []
  const week: Conversation[] = []
  const older: Conversation[] = []
  for (const c of list) {
    const t = new Date(c.updatedAt).getTime()
    if (t >= startOfToday.getTime()) today.push(c)
    else if (t >= startOfToday.getTime() - 6 * DAY) week.push(c)
    else older.push(c)
  }
  return [
    { label: "Hôm nay", items: today },
    { label: "7 ngày qua", items: week },
    { label: "Cũ hơn", items: older },
  ].filter((g) => g.items.length > 0)
}

export function AppSidebar({
  conversations,
  activeId,
  onNew,
  onSelect,
  onDelete,
}: AppSidebarProps) {
  const { isMobile, setOpenMobile } = useSidebar()
  // Trên điện thoại/tablet, chọn xong thì đóng ngăn kéo.
  const after = (fn: () => void) => () => {
    fn()
    if (isMobile) setOpenMobile(false)
  }
  const groups = groupConversations(conversations)

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader className="gap-3 p-3">
        <div className="flex items-center gap-2.5 px-1 pt-1">
          <div
            className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-(--user-bubble-from) to-(--user-bubble-to) text-white shadow-sm shadow-primary/25"
            aria-hidden="true"
          >
            <Bot className="size-5" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-base leading-tight font-semibold">
              {BOT_NAME}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              Lắng nghe và gợi ý nhạc theo cảm xúc
            </p>
          </div>
        </div>
        <Button
          type="button"
          onClick={after(onNew)}
          className="h-11 w-full cursor-pointer justify-start gap-2 rounded-xl bg-linear-to-br from-(--user-bubble-from) to-(--user-bubble-to) px-3 text-white shadow-md shadow-primary/25 hover:shadow-lg hover:shadow-primary/35"
        >
          <MessageSquarePlus className="size-5" aria-hidden="true" />
          Cuộc trò chuyện mới
        </Button>
      </SidebarHeader>

      <SidebarContent className="scroll-soft">
        {groups.length === 0 ? (
          <p className="px-4 py-6 text-sm text-muted-foreground">
            Chưa có cuộc trò chuyện nào. Gửi tin đầu tiên để bắt đầu nhé.
          </p>
        ) : (
          groups.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.items.map((c) => (
                    <SidebarMenuItem key={c.id}>
                      <SidebarMenuButton
                        isActive={c.id === activeId}
                        onClick={after(() => onSelect(c.id))}
                        className="h-10 cursor-pointer rounded-lg pr-9"
                        aria-current={c.id === activeId ? "page" : undefined}
                      >
                        <MessageSquare aria-hidden="true" />
                        <span className="truncate">{c.title}</span>
                      </SidebarMenuButton>
                      <SidebarMenuAction
                        showOnHover
                        onClick={() => onDelete(c.id)}
                        aria-label={`Xoá cuộc trò chuyện: ${c.title}`}
                        className="top-2 size-6 cursor-pointer hover:text-destructive"
                      >
                        <Trash2 aria-hidden="true" />
                      </SidebarMenuAction>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))
        )}
      </SidebarContent>

      <SidebarFooter className="p-3">
        <p className="px-1 text-xs leading-relaxed text-muted-foreground">
          Lịch sử chỉ lưu trên trình duyệt này. Đây không phải công cụ chẩn đoán
          tâm lý.
        </p>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
