import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export interface KeyboardShortcut {
  keys: string;
  description: string;
}

interface KeyboardShortcutsModalProps {
  open: boolean;
  onClose: () => void;
  shortcuts: KeyboardShortcut[];
}

export function KeyboardShortcutsModal({
  open,
  onClose,
  shortcuts,
}: KeyboardShortcutsModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <Card className="w-full max-w-xl border-border bg-background p-5">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-foreground">Keyboard Shortcuts</h3>
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-12 w-12"
            onClick={onClose}
            aria-label="Close keyboard shortcuts"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid gap-2 text-sm text-muted-foreground">
          {shortcuts.map((shortcut, idx) => (
            <p key={idx}>
              <span className="font-mono text-foreground">{shortcut.keys}</span>{" "}
              {shortcut.description}
            </p>
          ))}
        </div>
      </Card>
    </div>
  );
}
