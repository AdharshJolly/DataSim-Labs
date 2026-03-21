"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ThemedDropdownOption {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
  icon?: ReactNode;
}

interface ThemedDropdownProps {
  id?: string;
  name?: string;
  value: string;
  options: ThemedDropdownOption[];
  placeholder: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  buttonClassName?: string;
  menuClassName?: string;
  optionClassName?: string;
}

export function ThemedDropdown({
  id,
  name,
  value,
  options,
  placeholder,
  disabled = false,
  onChange,
  buttonClassName,
  menuClassName,
  optionClassName,
}: ThemedDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const listboxId = id ? `${id}-listbox` : undefined;

  const selectedOption = useMemo(
    () => options.find((option) => option.value === value),
    [options, value],
  );

  useEffect(() => {
    if (!isOpen) return;

    const selectedIndex = options.findIndex((option) => option.value === value);
    const nextIndex = selectedIndex >= 0 ? selectedIndex : 0;
    setActiveIndex(nextIndex);
  }, [isOpen, options, value]);

  useEffect(() => {
    const onOutsideClick = (event: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", onOutsideClick);
    return () => {
      document.removeEventListener("mousedown", onOutsideClick);
    };
  }, []);

  const moveActive = (direction: 1 | -1) => {
    if (options.length === 0) return;

    let nextIndex = activeIndex;
    for (let i = 0; i < options.length; i += 1) {
      nextIndex = (nextIndex + direction + options.length) % options.length;
      if (!options[nextIndex].disabled) {
        setActiveIndex(nextIndex);
        return;
      }
    }
  };

  const selectAtIndex = (index: number) => {
    const option = options[index];
    if (!option || option.disabled) return;
    onChange(option.value);
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
      {name && <input type="hidden" name={name} value={value} />}
      <button
        id={id}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        onClick={() => {
          if (disabled) return;
          setIsOpen((open) => !open);
        }}
        onKeyDown={(event) => {
          if (disabled) return;

          if (event.key === "ArrowDown") {
            event.preventDefault();
            if (!isOpen) {
              setIsOpen(true);
              return;
            }
            moveActive(1);
          }

          if (event.key === "ArrowUp") {
            event.preventDefault();
            if (!isOpen) {
              setIsOpen(true);
              return;
            }
            moveActive(-1);
          }

          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            if (!isOpen) {
              setIsOpen(true);
              return;
            }
            selectAtIndex(activeIndex);
          }

          if (event.key === "Escape") {
            event.preventDefault();
            setIsOpen(false);
          }
        }}
        className={cn(
          "group flex h-11 w-full items-center justify-between rounded-xl border border-border bg-[#0b0b13]/90 px-3 text-left text-sm text-foreground transition-colors",
          "hover:border-cyan-300/40 hover:bg-[#101321]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/40",
          "disabled:cursor-not-allowed disabled:opacity-60",
          buttonClassName,
        )}
      >
        <span className="flex min-w-0 items-center gap-2 pr-3">
          {selectedOption?.icon && (
            <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center text-cyan-200">
              {selectedOption.icon}
            </span>
          )}
          <span className="truncate">
            {selectedOption ? selectedOption.label : placeholder}
          </span>
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 flex-shrink-0 text-muted-foreground transition-transform group-hover:text-cyan-200",
            isOpen && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>

      {isOpen && !disabled && (
        <div
          className={cn(
            "absolute z-50 mt-2 max-h-72 w-full overflow-auto rounded-xl border border-border bg-[#0c0f1d] p-1 shadow-2xl shadow-black/50",
            menuClassName,
          )}
          role="listbox"
          id={listboxId}
          aria-labelledby={id}
        >
          {options.length === 0 ? (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              No options
            </div>
          ) : (
            options.map((option, index) => {
              const isSelected = option.value === value;
              const isActive = index === activeIndex;

              return (
                <button
                  key={option.value}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  disabled={option.disabled}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => selectAtIndex(index)}
                  className={cn(
                    "flex w-full items-start justify-between gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                    "text-foreground hover:bg-cyan-500/12 hover:text-cyan-100",
                    isActive && "bg-cyan-500/14 text-cyan-100",
                    isSelected && "border border-cyan-400/30 bg-cyan-500/18",
                    option.disabled && "cursor-not-allowed opacity-50",
                    optionClassName,
                  )}
                >
                  <span className="flex min-w-0 items-start gap-2">
                    {option.icon && (
                      <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center text-cyan-200/90">
                        {option.icon}
                      </span>
                    )}
                    <span className="min-w-0">
                      <span className="block truncate font-medium">
                        {option.label}
                      </span>
                      {option.description && (
                        <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                          {option.description}
                        </span>
                      )}
                    </span>
                  </span>
                  {isSelected && (
                    <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-cyan-200" />
                  )}
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
