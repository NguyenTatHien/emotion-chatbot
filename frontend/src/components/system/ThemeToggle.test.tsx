import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ThemeProvider } from "@/components/theme-provider"
import { ThemeToggle } from "./ThemeToggle"

function setup() {
  render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>
  )
  return userEvent.setup()
}

describe("ThemeToggle", () => {
  it("mặc định theo hệ thống (jsdom: sáng)", () => {
    setup()
    expect(
      screen.getByRole("button", { name: /Giao diện: theo hệ thống/ })
    ).toBeInTheDocument()
    expect(document.documentElement).toHaveClass("light")
  })

  it("chọn Tối thì gắn class dark, đổi color-scheme và nhớ lựa chọn", async () => {
    const user = setup()
    await user.click(screen.getByRole("button", { name: /Đổi giao diện/ }))
    await user.click(await screen.findByRole("menuitemradio", { name: "Tối" }))

    expect(document.documentElement).toHaveClass("dark")
    expect(document.documentElement).not.toHaveClass("light")
    expect(document.documentElement.style.colorScheme).toBe("dark")
    expect(localStorage.getItem("theme")).toBe("dark")
    expect(
      screen.getByRole("button", { name: /Giao diện: tối/ })
    ).toBeInTheDocument()
  })

  it("chọn Sáng sau khi đang tối", async () => {
    localStorage.setItem("theme", "dark")
    const user = setup()
    expect(document.documentElement).toHaveClass("dark")
    await user.click(screen.getByRole("button", { name: /Đổi giao diện/ }))
    await user.click(await screen.findByRole("menuitemradio", { name: "Sáng" }))
    expect(document.documentElement).toHaveClass("light")
    expect(localStorage.getItem("theme")).toBe("light")
  })
})
