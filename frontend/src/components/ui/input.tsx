import * as React from "react"

import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-lg border border-border bg-white/[0.03] px-3 py-2 text-sm text-foreground transition-all file:mr-4 file:cursor-pointer file:rounded-md file:border-0 file:bg-cyan-400/15 file:px-3 file:py-1 file:text-sm file:font-semibold file:text-cyan-100 hover:file:bg-cyan-400/20 placeholder:text-muted-foreground/40 focus:border-cyan-400/50 focus:bg-white/[0.06] focus:outline-none focus:ring-1 focus:ring-cyan-400/40 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
