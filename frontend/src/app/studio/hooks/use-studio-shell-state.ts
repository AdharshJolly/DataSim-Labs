"use client";

import { useState } from "react";

export function useStudioShellState() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [keyboardHelpOpen, setKeyboardHelpOpen] = useState(false);
  const [optimisticSaving, setOptimisticSaving] = useState(false);

  return {
    error,
    setError,
    busy,
    setBusy,
    mobileSidebarOpen,
    setMobileSidebarOpen,
    commandPaletteOpen,
    setCommandPaletteOpen,
    keyboardHelpOpen,
    setKeyboardHelpOpen,
    optimisticSaving,
    setOptimisticSaving,
  };
}
