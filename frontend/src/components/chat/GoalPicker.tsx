import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { GOALS, isGoal, type Goal } from "@/lib/goals"

interface GoalPickerProps {
  value: Goal | null
  onChange: (goal: Goal | null) => void
}

export function GoalPicker({ value, onChange }: GoalPickerProps) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span id="goal-label" className="shrink-0 text-sm text-muted-foreground">
        Mục tiêu nghe nhạc
      </span>
      <ToggleGroup
        type="single"
        variant="outline"
        spacing={1}
        aria-labelledby="goal-label"
        className="w-full flex-1 sm:w-auto"
        value={value ?? ""}
        onValueChange={(v) => onChange(isGoal(v) ? v : null)}
      >
        {GOALS.map((g) => (
          <ToggleGroupItem
            key={g.value}
            value={g.value}
            className="h-10 flex-1 cursor-pointer rounded-full! border-border/80 bg-card/70 px-1 text-sm backdrop-blur data-[state=on]:border-transparent data-[state=on]:bg-linear-to-br data-[state=on]:from-(--user-bubble-from) data-[state=on]:to-(--user-bubble-to) data-[state=on]:text-white data-[state=on]:shadow-sm data-[state=on]:shadow-primary/30 sm:flex-none sm:px-4"
          >
            {g.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  )
}
