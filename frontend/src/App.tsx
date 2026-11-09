import { ChatView } from "@/components/chat/ChatView"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"

export function App() {
  return (
    <TooltipProvider>
      <ChatView />
      <Toaster position="top-center" />
    </TooltipProvider>
  )
}

export default App
