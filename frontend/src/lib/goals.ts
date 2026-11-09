export const GOALS = [
  { value: "xoa_diu", label: "Xoa dịu" },
  { value: "nang_mood", label: "Nâng mood" },
  { value: "tap_trung", label: "Tập trung" },
  { value: "giai_toa", label: "Giải toả" },
] as const

export type Goal = (typeof GOALS)[number]["value"]

export function isGoal(value: string | null | undefined): value is Goal {
  return GOALS.some((g) => g.value === value)
}
