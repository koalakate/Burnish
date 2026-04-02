"use client";

import { use, useState, useCallback } from "react";
import Link from "next/link";
import {
  useCorrections,
  useCheckRun,
  useAcceptCorrection,
  useDismissCorrection,
  useEditCorrection,
  useFixAll,
  useExport,
} from "@/lib/queries";
import { CorrectionView } from "@/components/correction-view";
import { CorrectionCard } from "@/components/correction-card";
import { DqsBadge } from "@/components/dqs-badge";
import { Button } from "@/components/ui/button";
import type { Correction } from "@/lib/types";
import { Check, Download, Loader2 } from "lucide-react";

export default function CorrectionsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: checkRunId } = use(params);
  const { data: correctionsData, isLoading, error } = useCorrections(checkRunId);
  const { data: checkRunData } = useCheckRun(checkRunId);
  const acceptMutation = useAcceptCorrection(checkRunId);
  const dismissMutation = useDismissCorrection(checkRunId);
  const editMutation = useEditCorrection(checkRunId);
  const fixAllMutation = useFixAll(checkRunId);

  const [selectedCorrectionId, setSelectedCorrectionId] = useState<string | null>(null);
  const [activeSlideIndex, setActiveSlideIndex] = useState(0);
  const [showExport, setShowExport] = useState(false);

  const { data: exportData } = useExport(checkRunId, showExport);

  const handleAccept = useCallback(
    (correctionId: string) => acceptMutation.mutate(correctionId),
    [acceptMutation]
  );

  const handleDismiss = useCallback(
    (correctionId: string) => dismissMutation.mutate(correctionId),
    [dismissMutation]
  );

  const handleEdit = useCallback(
    (correctionId: string, value: string) => {
      editMutation.mutate({ correctionId, value });
    },
    [editMutation]
  );

  const handleFixAll = useCallback(() => {
    fixAllMutation.mutate(undefined, {
      onSuccess: () => setShowExport(true),
    });
  }, [fixAllMutation]);

  const handleDownload = useCallback(() => {
    if (!exportData?.download_url) return;
    const a = document.createElement("a");
    a.href = exportData.download_url;
    a.download = "corrected-deck.pptx";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [exportData]);

  const handleCorrectionClick = useCallback((correction: Correction) => {
    setSelectedCorrectionId((prev) =>
      prev === correction.id ? null : correction.id
    );
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-muted/50 rounded w-48 animate-pulse" />
        <div className="flex gap-4 h-[calc(100vh-10rem)]">
          <div className="flex-1 bg-muted/30 rounded-lg animate-pulse" />
          <div className="w-80 bg-muted/20 rounded-lg animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !correctionsData) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center">
        <p className="text-sm text-destructive">
          Failed to load corrections.
        </p>
      </div>
    );
  }

  const slides = correctionsData.slides;
  const activeSlide = slides[activeSlideIndex];
  const allCorrections = slides.flatMap((s) => s.corrections);
  const pendingCount = allCorrections.filter((c) => c.correction_status === "pending").length;
  const allResolved = pendingCount === 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 text-sm">
        <Link
          href={`/checks/${checkRunId}`}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          Check Results
        </Link>
        <span className="text-muted-foreground/40">/</span>
        <span className="text-foreground">Corrections</span>

        <div className="ml-auto flex items-center gap-2">
          {/* Fix All button */}
          {pendingCount > 0 && (
            <Button
              variant="default"
              size="sm"
              onClick={handleFixAll}
              disabled={fixAllMutation.isPending}
            >
              {fixAllMutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" data-icon="inline-start" />
                  Fixing...
                </>
              ) : (
                <>
                  <Check className="size-3.5" data-icon="inline-start" />
                  Fix All ({pendingCount})
                </>
              )}
            </Button>
          )}

          {/* Download button */}
          {(allResolved || showExport) && exportData && (
            <Button variant="default" size="sm" onClick={handleDownload}>
              <Download className="size-3.5" data-icon="inline-start" />
              Download PPTX
            </Button>
          )}
        </div>
      </div>

      {/* Download confirmation with DQS */}
      {showExport && exportData && (
        <div className="rounded-lg border border-dqs-good/30 bg-dqs-good/5 p-4 flex items-center gap-4">
          {exportData.dqs_after != null && <DqsBadge score={exportData.dqs_after} size="lg" />}
          <div>
            <p className="text-sm font-medium">Corrections applied</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Your corrected deck is ready to download.
            </p>
          </div>
          <Button
            variant="default"
            size="sm"
            className="ml-auto"
            onClick={handleDownload}
          >
            <Download className="size-3.5" data-icon="inline-start" />
            Download PPTX
          </Button>
        </div>
      )}

      {/* Slide tabs */}
      {slides.length > 1 && (
        <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
          {slides.map((slide, idx) => {
            const slidePending = slide.corrections.filter(
              (c) => c.correction_status === "pending"
            ).length;
            return (
              <button
                key={slide.slide_index}
                onClick={() => setActiveSlideIndex(idx)}
                className={`shrink-0 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  idx === activeSlideIndex
                    ? "bg-brand-400/15 text-brand-400"
                    : "text-muted-foreground hover:bg-muted/30"
                }`}
              >
                Slide {slide.slide_index + 1}
                {slidePending > 0 && (
                  <span className="ml-1.5 inline-flex items-center justify-center size-4 rounded-full bg-severity-warning/20 text-severity-warning text-[10px]">
                    {slidePending}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Main content: side-by-side view + correction panel */}
      {activeSlide && (
        <div className="flex gap-4 h-[calc(100vh-14rem)]">
          {/* Side-by-side slide preview */}
          <div className="flex-1 min-w-0">
            <CorrectionView
              originalThumbnailUrl={
                checkRunData?.slides?.find(
                  (s) => s.slide_index === activeSlide.slide_index
                )?.thumbnail_url ?? null
              }
              correctedThumbnailUrl={
                checkRunData?.slides?.find(
                  (s) => s.slide_index === activeSlide.slide_index
                )?.corrected_thumbnail_url ?? null
              }
              corrections={activeSlide.corrections}
              selectedCorrectionId={selectedCorrectionId}
              onCorrectionClick={handleCorrectionClick}
            />
          </div>

          {/* Correction panel (right) */}
          <div className="w-80 shrink-0 rounded-lg border border-border/50 bg-card overflow-hidden flex flex-col">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50">
              <span className="text-sm font-medium">Corrections</span>
              <span className="ml-auto text-xs tabular-nums text-muted-foreground">
                {activeSlide.corrections.length} total
              </span>
            </div>
            <div className="flex-1 overflow-y-auto">
              {activeSlide.corrections.map((correction) => (
                <CorrectionCard
                  key={correction.id}
                  correction={correction}
                  isSelected={correction.id === selectedCorrectionId}
                  onSelect={() => handleCorrectionClick(correction)}
                  onAccept={handleAccept}
                  onDismiss={handleDismiss}
                  onEdit={handleEdit}
                />
              ))}
              {activeSlide.corrections.length === 0 && (
                <div className="px-4 py-8 text-center">
                  <p className="text-sm text-muted-foreground">
                    No corrections for this slide.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
