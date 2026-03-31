"use client";

import { useMemo, useRef, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export interface CorrelationRule {
  source: string;
  target: string;
  strength: number;
}

interface RelationshipBuilderProps {
  attributeNames: string[];
  rules: CorrelationRule[];
  onChange: (rules: CorrelationRule[]) => void;
}

const clampStrength = (value: number): number =>
  Math.max(-1, Math.min(1, Number(value.toFixed(2))));

interface DragState {
  source: string;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

export function RelationshipBuilder({
  attributeNames,
  rules,
  onChange,
}: RelationshipBuilderProps) {
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [strength, setStrength] = useState(0.6);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [hoveredTarget, setHoveredTarget] = useState<string | null>(null);

  const names = useMemo(
    () => attributeNames.filter((name) => name.trim().length > 0),
    [attributeNames],
  );

  const indexByName = useMemo(() => {
    const map = new Map<string, number>();
    names.forEach((name, idx) => map.set(name, idx));
    return map;
  }, [names]);

  const safeRules = useMemo(
    () =>
      rules.filter(
        (rule) =>
          indexByName.has(rule.source) &&
          indexByName.has(rule.target) &&
          rule.source !== rule.target,
      ),
    [indexByName, rules],
  );

  const toGraphPoint = (clientX: number, clientY: number) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) {
      return { x: 0, y: 0 };
    }
    const x = ((clientX - rect.left) / rect.width) * 1000;
    const y = ((clientY - rect.top) / rect.height) * graphHeight;
    return { x, y };
  };

  const ruleY = (idx: number) => 24 + idx * 42;

  const startDrag = (sourceName: string) => {
    const sourceIdx = indexByName.get(sourceName);
    if (sourceIdx == null) {
      return;
    }

    const y = ruleY(sourceIdx);
    setSource(sourceName);
    setDragState({
      source: sourceName,
      startX: 200,
      startY: y,
      currentX: 200,
      currentY: y,
    });
  };

  const handleCanvasMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!dragState) {
      return;
    }
    const point = toGraphPoint(event.clientX, event.clientY);
    setDragState((prev) =>
      prev
        ? {
            ...prev,
            currentX: point.x,
            currentY: point.y,
          }
        : null,
    );
  };

  const cancelDrag = () => {
    setDragState(null);
    setHoveredTarget(null);
  };

  const addRule = () => {
    const s = source.trim();
    const t = target.trim();
    if (!s || !t || s === t) return;

    const normalizedStrength = clampStrength(strength);
    const existingIndex = safeRules.findIndex(
      (rule) => rule.source === s && rule.target === t,
    );

    if (existingIndex >= 0) {
      const next = [...safeRules];
      next[existingIndex] = {
        ...next[existingIndex],
        strength: normalizedStrength,
      };
      onChange(next);
      return;
    }

    onChange([
      ...safeRules,
      { source: s, target: t, strength: normalizedStrength },
    ]);
  };

  const connectFromDrag = (targetName: string) => {
    const activeSource = dragState?.source || source;
    if (!activeSource || activeSource === targetName) {
      cancelDrag();
      return;
    }

    const normalizedStrength = clampStrength(strength);
    const existingIndex = safeRules.findIndex(
      (rule) => rule.source === activeSource && rule.target === targetName,
    );

    if (existingIndex >= 0) {
      const next = [...safeRules];
      next[existingIndex] = {
        ...next[existingIndex],
        strength: normalizedStrength,
      };
      onChange(next);
    } else {
      onChange([
        ...safeRules,
        {
          source: activeSource,
          target: targetName,
          strength: normalizedStrength,
        },
      ]);
    }

    setTarget(targetName);
    cancelDrag();
  };

  const updateRuleStrength = (idx: number, value: number) => {
    const next = [...safeRules];
    next[idx] = { ...next[idx], strength: clampStrength(value) };
    onChange(next);
  };

  const removeRule = (idx: number) => {
    onChange(safeRules.filter((_, i) => i !== idx));
  };

  const graphHeight = Math.max(220, names.length * 42 + 40);

  return (
    <Card className="mb-8 overflow-hidden border-border bg-card/70">
      <div className="border-b border-border/60 px-4 py-3">
        <p className="text-sm font-semibold text-foreground">
          Visual Relationship Builder
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Build correlations as directed edges between fields. Strength supports
          -1.0 to 1.0.
        </p>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[1.35fr_1fr]">
        <div
          ref={canvasRef}
          className="relative rounded-lg border border-border/60 bg-background/40"
          style={{ minHeight: graphHeight }}
          onMouseMove={handleCanvasMouseMove}
          onMouseLeave={cancelDrag}
          onMouseUp={cancelDrag}
        >
          <svg
            viewBox={`0 0 1000 ${graphHeight}`}
            className="pointer-events-none absolute inset-0 h-full w-full"
            aria-hidden="true"
          >
            <defs>
              <marker
                id="edge-arrow"
                markerWidth="8"
                markerHeight="8"
                refX="7"
                refY="4"
                orient="auto"
              >
                <path d="M0,0 L8,4 L0,8 z" fill="#94a3b8" />
              </marker>
            </defs>
            {safeRules.map((rule, idx) => {
              const sourceIdx = indexByName.get(rule.source);
              const targetIdx = indexByName.get(rule.target);
              if (sourceIdx == null || targetIdx == null) {
                return null;
              }

              const y1 = ruleY(sourceIdx);
              const y2 = ruleY(targetIdx);
              const midX = 500;
              const stroke = rule.strength >= 0 ? "#2dd4bf" : "#f97316";
              const opacity = Math.max(0.25, Math.abs(rule.strength));

              return (
                <path
                  key={`${rule.source}-${rule.target}-${idx}`}
                  d={`M 200 ${y1} C ${midX} ${y1}, ${midX} ${y2}, 800 ${y2}`}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={2 + Math.abs(rule.strength) * 2}
                  opacity={opacity}
                  markerEnd="url(#edge-arrow)"
                />
              );
            })}

            {dragState ? (
              <path
                d={`M ${dragState.startX} ${dragState.startY} C 500 ${dragState.startY}, 500 ${dragState.currentY}, ${dragState.currentX} ${dragState.currentY}`}
                fill="none"
                stroke="#e2e8f0"
                strokeDasharray="6 4"
                strokeWidth={2}
                opacity={0.9}
              />
            ) : null}
          </svg>

          <div className="grid grid-cols-2 gap-6 px-4 py-3">
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Source Fields
              </p>
              <div className="space-y-2">
                {names.map((name) => (
                  <button
                    type="button"
                    key={`left-${name}`}
                    className="w-full rounded-md border border-cyan-300/20 bg-cyan-500/10 px-2.5 py-1.5 text-left text-xs text-cyan-200 transition hover:border-cyan-200/60 hover:bg-cyan-500/20"
                    onMouseDown={(event) => {
                      event.preventDefault();
                      startDrag(name);
                    }}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Target Fields
              </p>
              <div className="space-y-2">
                {names.map((name) => (
                  <button
                    type="button"
                    key={`right-${name}`}
                    className={
                      "w-full rounded-md border px-2.5 py-1.5 text-left text-xs transition " +
                      (hoveredTarget === name
                        ? "border-violet-200/80 bg-violet-500/30 text-violet-100"
                        : "border-violet-300/20 bg-violet-500/10 text-violet-200 hover:border-violet-200/60 hover:bg-violet-500/20")
                    }
                    onMouseEnter={() => setHoveredTarget(name)}
                    onMouseLeave={() =>
                      setHoveredTarget((prev) => (prev === name ? null : prev))
                    }
                    onMouseUp={(event) => {
                      event.preventDefault();
                      if (dragState) {
                        connectFromDrag(name);
                      }
                    }}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-border/60 bg-background/40 p-3">
            <p className="text-xs text-muted-foreground">
              Drag mode: press a source field on the left and release on a
              target field on the right.
            </p>
          </div>

          <div className="rounded-lg border border-border/60 bg-background/40 p-3">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Add Edge
            </p>

            <div className="grid gap-2">
              <label className="text-xs text-muted-foreground">Source</label>
              <select
                className="w-full"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="">Select source</option>
                {names.map((name) => (
                  <option key={`source-${name}`} value={name}>
                    {name}
                  </option>
                ))}
              </select>

              <label className="mt-2 text-xs text-muted-foreground">
                Target
              </label>
              <select
                className="w-full"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              >
                <option value="">Select target</option>
                {names.map((name) => (
                  <option key={`target-${name}`} value={name}>
                    {name}
                  </option>
                ))}
              </select>

              <label className="mt-2 text-xs text-muted-foreground">
                Strength:{" "}
                <span className="font-mono">{strength.toFixed(2)}</span>
              </label>
              <input
                type="range"
                min={-1}
                max={1}
                step={0.05}
                value={strength}
                onChange={(e) => setStrength(Number(e.target.value))}
              />

              <Button
                type="button"
                variant="default"
                className="mt-2"
                onClick={addRule}
                disabled={!source || !target || source === target}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Relationship
              </Button>
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-background/40 p-3">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Relationships ({safeRules.length})
            </p>

            <div className="space-y-3">
              {safeRules.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No relationships defined yet.
                </p>
              ) : (
                safeRules.map((rule, idx) => (
                  <div
                    key={`${rule.source}-${rule.target}-${idx}`}
                    className="rounded-md border border-border/60 bg-background/70 p-2"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2 text-xs">
                      <span className="truncate text-foreground">
                        {rule.source} -&gt; {rule.target}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeRule(idx)}
                        className="rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                        aria-label="Remove relationship"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <input
                      type="range"
                      min={-1}
                      max={1}
                      step={0.05}
                      value={rule.strength}
                      onChange={(e) =>
                        updateRuleStrength(idx, Number(e.target.value))
                      }
                    />
                    <p className="mt-1 text-[11px] font-mono text-muted-foreground">
                      strength={rule.strength.toFixed(2)}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
