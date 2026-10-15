"use client"

import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, Loader2Icon } from "lucide-react"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      icons={{
        success: (
          <CircleCheckIcon className="size-4" />
        ),
        info: (
          <InfoIcon className="size-4" />
        ),
        warning: (
          <TriangleAlertIcon className="size-4 text-attention" />
        ),
        error: (
          <TriangleAlertIcon className="size-4 text-attention" />
        ),
        loading: (
          <Loader2Icon className="size-4 animate-spin" />
        ),
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "20px",
          "--normal-bg-hover": "var(--raised)",
        } as React.CSSProperties
      }
      duration={5000}
      // Above the phone bottom nav and its safe area.
      mobileOffset={{ bottom: "calc(80px + env(safe-area-inset-bottom))" }}
      toastOptions={{
        classNames: {
          toast: "cn-toast font-sans! text-[15px]! shadow-floating!",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
