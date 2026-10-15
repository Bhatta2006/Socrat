import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

// Chips: outlined pills, no fill. On a colour card the outline takes the card's text colour.
const badgeVariants = cva(
  "group/badge inline-flex h-7 w-fit shrink-0 items-center justify-center gap-1.5 overflow-hidden rounded-full border px-3 text-[13px] leading-none font-semibold whitespace-nowrap transition-colors has-data-[icon=inline-end]:pr-2.5 has-data-[icon=inline-start]:pl-2.5 [[data-tone=hero]_&]:border-current [[data-tone=hero]_&]:text-current [[data-tone=lilac]_&]:border-current [[data-tone=lilac]_&]:text-current [[data-tone=cream]_&]:border-current [[data-tone=cream]_&]:text-current [&>svg]:pointer-events-none [&>svg]:size-3.5! [&>svg]:stroke-[1.75]",
  {
    variants: {
      variant: {
        default: "border-border-strong text-foreground",
        outline: "border-border-strong text-foreground [a]:hover:bg-raised",
        secondary: "border-transparent bg-raised text-foreground",
        destructive: "border-attention text-attention",
        ghost: "border-transparent text-muted-foreground",
        link: "border-transparent px-0 text-foreground underline underline-offset-4",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
