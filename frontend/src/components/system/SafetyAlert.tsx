import { HeartHandshake } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

export function SafetyAlert({ text }: { text: string }) {
  return (
    <Alert
      role="alert"
      className="border-2 border-primary bg-primary/5 text-foreground"
    >
      <HeartHandshake className="text-primary" aria-hidden="true" />
      <AlertTitle className="text-base font-semibold">
        Bạn không đơn độc
      </AlertTitle>
      <AlertDescription className="whitespace-pre-wrap text-base text-foreground">
        {text}
      </AlertDescription>
    </Alert>
  )
}
