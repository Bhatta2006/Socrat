import { cn } from "cn"

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse-slow rounded-xl bg-raised", className)}
      {...props}
    />
  )
}

export { Skeleton }
