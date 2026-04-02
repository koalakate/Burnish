"use client";

import { use, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import { useCheckRun } from "@/lib/queries";
import { DqsBadge } from "@/components/dqs-badge";
import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/types";

function maxSeverity(dqs: number): Severity {
  if (dqs >= 80) return "info";
  if (dqs >= 60) return "warning";
  return "error";
}

export default function CheckResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: checkRun, isLoading, error } = useCheckRun(id);

  const isPolling = checkRun?.status === "queued" || checkRun?.status === "running";

  const issueTotals = useMemo(() => {
    if (!checkRun) return { error: 0, warning: 0, info: 0 };
    return {
      error: checkRun.issue_count_error,
      warning: checkRun.issue_count_warning,
      info: checkRun.issue_count_info,
    };
  }, [checkRun]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-muted/50 rounded w-48 animate-pulse" />
        <div className="h-24 bg-muted/30 rounded-lg animate-pulse" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="aspect-video bg-muted/30 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !checkRun) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center">
        <p className="text-sm text-destructive">
          Failed to load check results. Please try again.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-mono text-2xl font-medium tracking-tight mb-1">
            Check Results
          </h2>
          <p className="text-sm text-muted-foreground">
            {isPolling
              ? "Checking your deck..."
              : checkRun.status === "complete"
                ? "Check complete"
                : "Check failed"}
          </p>
        </div>
        {checkRun.dqs_overall != null && (
          <DqsBadge score={checkRun.dqs_overall} size="lg" />
        )}
      </div>

      {/* Polling indicator */}
      {isPolling && (
        <div className="rounded-lg border border-brand-400/30 bg-brand-400/5 p-4 flex items-center gap-3">
          <div className="size-4 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
          <span className="text-sm text-foreground/80">
            Analyzing your presentation...
          </span>
        </div>
      )}

      {/* Issue count summary */}
      {checkRun.status === "complete" && (
        <div className="flex items-center gap-4">
          {issueTotals.error > 0 && (
            <div className="flex items-center gap-1.5 text-sm">
              <span className="size-2 rounded-full bg-severity-error" />
              <span className="tabular-nums">{issueTotals.error}</span>
              <span className="text-muted-foreground">error{issueTotals.error !== 1 ? "s" : ""}</span>
            </div>
          )}
          {issueTotals.warning > 0 && (
            <div className="flex items-center gap-1.5 text-sm">
              <span className="size-2 rounded-full bg-severity-warning" />
              <span className="tabular-nums">{issueTotals.warning}</span>
              <span className="text-muted-foreground">warning{issueTotals.warning !== 1 ? "s" : ""}</span>
            </div>
          )}
          {issueTotals.info > 0 && (
            <div className="flex items-center gap-1.5 text-sm">
              <span className="size-2 rounded-full bg-brand-400" />
              <span className="tabular-nums">{issueTotals.info}</span>
              <span className="text-muted-foreground">info</span>
            </div>
          )}
          {issueTotals.error === 0 && issueTotals.warning === 0 && issueTotals.info === 0 && (
            <span className="text-sm text-dqs-good">No issues found</span>
          )}
        </div>
      )}

      {/* Slide strip — horizontal scrollable row of thumbnails */}
      {checkRun.slides && checkRun.slides.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-3">Slides</h3>
          <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
            {checkRun.slides.map((slide) => {
              const severity = maxSeverity(slide.dqs_slide);
              return (
                <Link
                  key={slide.slide_index}
                  href={`/checks/${id}/slides/${slide.slide_index}`}
                  className="group shrink-0 w-48"
                >
                  <div className="relative aspect-video rounded-md bg-muted/50 overflow-hidden border border-border/50 transition-all group-hover:border-border group-hover:shadow-md">
                    {slide.thumbnail_url ? (
                      <Image
                        src={slide.thumbnail_url}
                        alt={`Slide ${slide.slide_index + 1}`}
                        fill
                        className="object-cover"
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="font-mono text-lg text-muted-foreground/20">▦</span>
                      </div>
                    )}
                    {/* Severity dot */}
                    <div className="absolute top-1.5 right-1.5">
                      <span
                        className={cn(
                          "block size-2.5 rounded-full ring-2 ring-card",
                          severity === "error" && "bg-severity-error",
                          severity === "warning" && "bg-severity-warning",
                          severity === "info" && "bg-dqs-good"
                        )}
                      />
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-1.5 px-0.5">
                    <span className="text-xs text-muted-foreground">
                      Slide {slide.slide_index + 1}
                    </span>
                    <DqsBadge score={slide.dqs_slide} size="sm" />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
