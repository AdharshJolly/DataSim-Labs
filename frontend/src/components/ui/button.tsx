import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/40 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border border-cyan-300/30 bg-cyan-400/15 text-cyan-100 hover:bg-cyan-400/25",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-border bg-transparent hover:border-cyan-300/40 hover:text-cyan-200",
        secondary:
          "bg-white/5 border border-border text-foreground hover:bg-white/10",
        ghost: "hover:bg-cyan-500/12 hover:text-cyan-100",
        link: "text-cyan-400 underline-offset-4 hover:underline",
        cyber:
          "relative overflow-hidden border border-border bg-background px-6 transition-all duration-300 hover:border-cyan-400/50 hover:shadow-[0_0_15px_2px_rgba(34,211,238,0.1)] before:absolute before:inset-0 before:-left-[50%] before:bg-gradient-to-r before:from-transparent before:via-cyan-400/20 before:to-transparent before:skew-x-[-25deg] before:transition-all before:duration-500 hover:before:left-[100%]",
      },
      size: {
        default: "h-11 px-5 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-12 rounded-lg px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
