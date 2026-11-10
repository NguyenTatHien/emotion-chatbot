import { ChatView } from "@/components/chat/ChatView"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"

export function App() {
  return (
    <ThemeProvider>
      <TooltipProvider>
        <ChatView />
        <Toaster position="top-center" />
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
