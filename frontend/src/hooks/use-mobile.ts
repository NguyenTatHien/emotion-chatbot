import * as React from "react"

/** Dưới 1024px (điện thoại, tablet): sidebar là ngăn kéo; từ 1024px: sidebar cố định. */
export const MOBILE_BREAKPOINT = 1024
const QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

function current(): boolean {
  if (typeof window === "undefined") return false
  return window.innerWidth < MOBILE_BREAKPOINT
}

export function useIsMobile() {
  // Khởi tạo đồng bộ để lần vẽ đầu đã đúng bố cục (không nháy sidebar trên điện thoại).
  const [isMobile, setIsMobile] = React.useState<boolean>(current)

  React.useEffect(() => {
    const mql = window.matchMedia(QUERY)
    const onChange = () => setIsMobile(current())
    mql.addEventListener("change", onChange)
    onChange()
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return isMobile
}
