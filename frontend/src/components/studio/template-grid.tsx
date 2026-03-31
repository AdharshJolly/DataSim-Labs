"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Check, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { listDatasetTemplates, type DatasetTemplate } from "@/lib/api-client";

export type Template = DatasetTemplate;

interface TemplateGridProps {
  onSelectTemplate?: (template: Template) => void | Promise<void>;
  isLoading?: boolean;
  showCreateLink?: boolean;
}

export function TemplateGrid({
  onSelectTemplate,
  isLoading = false,
  showCreateLink = true,
}: TemplateGridProps) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(isLoading);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        setLoading(true);
        const data = await listDatasetTemplates();
        setTemplates(data.templates ?? []);
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load templates",
        );
        setTemplates([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTemplates();
  }, []);

  const handleSelectTemplate = async (template: Template) => {
    setSelectedId(template.id);
    try {
      await onSelectTemplate?.(template);
    } finally {
      setSelectedId(null);
    }
  };

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <Card
            key={i}
            className="h-48 animate-pulse bg-gradient-to-br from-card/90 to-transparent"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
        <p className="font-medium">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((template) => (
          <Card
            key={template.id}
            className="group relative flex flex-col gap-3 rounded-2xl bg-gradient-to-br from-card/90 to-transparent p-5 backdrop-blur-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/50 hover:shadow-xl hover:shadow-primary/10"
          >
            <div className="absolute right-3 top-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-primary">
                <Zap className="h-4 w-4" />
              </div>
            </div>

            <div className="min-w-0 pr-8">
              <h3 className="font-display text-lg font-bold text-foreground">
                {template.name}
              </h3>
              <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
                {template.description}
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {template.domain && (
                  <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[11px] text-primary">
                    {template.domain}
                  </span>
                )}
                {template.complexity && (
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                    {template.complexity}
                  </span>
                )}
              </div>
            </div>

            {template.columns && (
              <div className="space-y-2 border-t border-border/30 pt-3">
                <p className="text-xs font-medium text-muted-foreground">
                  Columns: {Object.keys(template.columns).length}
                </p>
                {template.recommended_row_range && (
                  <p className="text-[11px] text-muted-foreground">
                    Recommended rows:{" "}
                    {template.recommended_row_range.min.toLocaleString()} -{" "}
                    {template.recommended_row_range.max.toLocaleString()}
                  </p>
                )}
                <div className="flex flex-wrap gap-1">
                  {Object.keys(template.columns)
                    .slice(0, 4)
                    .map((col) => (
                      <span
                        key={col}
                        className="inline-block rounded-full bg-primary/20 px-2 py-0.5 text-xs text-primary"
                      >
                        {col}
                      </span>
                    ))}
                  {Object.keys(template.columns).length > 4 && (
                    <span className="inline-block rounded-full bg-primary/10 px-2 py-0.5 text-xs text-muted-foreground">
                      +{Object.keys(template.columns).length - 4} more
                    </span>
                  )}
                </div>
                {template.tags && template.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {template.tags.slice(0, 3).map((tag) => (
                      <span
                        key={`${template.id}-${tag}`}
                        className="inline-block rounded-full bg-cyan-500/15 px-2 py-0.5 text-[11px] text-cyan-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="mt-auto flex gap-2 pt-2">
              <Button
                variant="cyber"
                className="flex-1 text-xs"
                disabled={selectedId === template.id}
                onClick={() => handleSelectTemplate(template)}
              >
                <Check className="mr-1.5 h-3 w-3" />
                {selectedId === template.id ? "Applying..." : "Use Template"}
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {showCreateLink && (
        <Card className="rounded-2xl border-dashed bg-gradient-to-br from-card/80 to-transparent p-6 text-center">
          <h3 className="font-display text-lg font-bold">Start from Scratch</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Prefer to build your own schema? No problem!
          </p>
          <Button asChild variant="outline" className="mt-4">
            <Link href="/studio?new=true">Create Blank Dataset</Link>
          </Button>
        </Card>
      )}
    </div>
  );
}
