"use client";

import { MoonStar, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useThemeMode } from "@/components/ui/theme-provider";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useThemeMode();

  const handleToggle = () => {
    const nextTheme = resolvedTheme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
  };

  const Icon = resolvedTheme === "dark" ? Sun : MoonStar;

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      className="h-10 w-10"
      onClick={handleToggle}
      aria-label={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} mode`}
    >
      <Icon className="h-4 w-4" />
    </Button>
  );
}
