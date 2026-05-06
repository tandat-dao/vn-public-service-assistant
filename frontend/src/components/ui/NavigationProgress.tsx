"use client"

import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"

export function NavigationProgress() {
  const pathname = usePathname()
  const [state, setState] = useState<"idle" | "loading" | "complete">("idle")

  useEffect(() => {
    setState("loading")
    const timer = setTimeout(() => {
      setState("complete")
      setTimeout(() => setState("idle"), 500)
    }, 300)
    return () => clearTimeout(timer)
  }, [pathname])

  if (state === "idle") return null

  return (
    <div className={`nprogress-bar ${state}`} />
  )
}
