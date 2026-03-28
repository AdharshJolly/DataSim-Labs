import * as React from "react";
import { Command } from "cmdk";

import { cn } from "@/lib/utils";

interface StudioCommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  label?: string;
  placeholder?: string;
  emptyLabel?: string;
  className?: string;
  children: React.ReactNode;
}

interface StudioCommandGroupProps {
  heading: string;
  className?: string;
  children: React.ReactNode;
}

type StudioCommandItemProps = React.ComponentPropsWithoutRef<
  typeof Command.Item
>;

export function StudioCommandPalette({
  open,
  onOpenChange,
  label = "Command Palette",
  placeholder = "Type a command...",
  emptyLabel = "No matching commands",
  className,
  children,
}: StudioCommandPaletteProps) {
  return (
    <Command.Dialog
      open={open}
      onOpenChange={onOpenChange}
      label={label}
      className={cn(
        "fixed left-1/2 top-24 z-[120] w-[min(680px,92vw)] -translate-x-1/2 overflow-hidden rounded-xl border border-border bg-background shadow-2xl",
        className,
      )}
    >
      <div className="border-b border-border px-3 py-2">
        <Command.Input
          autoFocus
          placeholder={placeholder}
          className="h-12 w-full bg-transparent text-sm text-foreground outline-none"
        />
      </div>
      <Command.List className="max-h-[360px] overflow-y-auto p-2">
        <Command.Empty className="px-3 py-6 text-sm text-muted-foreground">
          {emptyLabel}
        </Command.Empty>
        {children}
      </Command.List>
    </Command.Dialog>
  );
}

export function StudioCommandGroup({
  heading,
  className,
  children,
}: StudioCommandGroupProps) {
  return (
    <Command.Group
      heading={heading}
      className={cn("text-xs text-muted-foreground", className)}
    >
      {children}
    </Command.Group>
  );
}

export function StudioCommandItem({
  className,
  children,
  ...props
}: StudioCommandItemProps) {
  return (
    <Command.Item
      className={cn(
        "flex min-h-12 cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm text-foreground aria-selected:bg-white/10",
        className,
      )}
      {...props}
    >
      {children}
    </Command.Item>
  );
}
