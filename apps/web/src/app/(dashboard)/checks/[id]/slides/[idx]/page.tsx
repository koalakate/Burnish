"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useSlideDetail } from "@/lib/queries";
import { SlidePreview } from "@/components/slide-preview";
import { CheckPanel } from "@/components/check-panel";
import { DqsBadge } from "@/components/dqs-badge";
import type { Issue } from "@/lib/types";

export default function SlideDetailPage({
  params,
}: {
  params: Promise<{ id: string; idx: string }>;
}) {
  const { id, idx } = use(params);
  const slideIndex = parseInt(idx, 10);
  const { data: slide, isLoading, error } = useSlideDetail(id, slideIndex);
  const [selectedIssue, setSelectedIssue] = useState<string | null>(null);

  const handleIssueClick = (issue: Issue) => {
    setSelectedIssue((prev) => (prev === issue.id ? null : issue.id));
  };

  if (isLoading) {
    return (
      <div className="flex gap-6 h-[calc(100vh-7rem)]">
        <div className="flex-1 bg-muted/30 rounded-lg animate-pulse" />
        <div className="w-80 bg-muted/20 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error || !slide) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center">
        <p className="text-sm text-destructive">
          Failed to load slide details.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link
          href={`/checks/${id}`}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          Check Results
        </Link>
        <span className="text-muted-foreground/40">/</span>
        <span className="text-foreground">
          Slide {slideIndex + 1}
        </span>
        <div className="ml-auto">
          <DqsBadge score={slide.dqs_slide} size="sm" />
        </div>
      </div>

      {/* Main content: slide preview + issue panel */}
      <div className="flex gap-4 h-[calc(100vh-10rem)]">
        {/* Slide preview (left) */}
        <div className="flex-1 min-w-0">
          <SlidePreview
            thumbnailUrl={slide.thumbnail_url}
            issues={slide.issues}
            selectedIssueId={selectedIssue}
            onIssueClick={handleIssueClick}
            className="relative w-full rounded-lg overflow-hidden border border-border/50"
          />
        </div>

        {/* Issue panel (right) */}
        <div className="w-80 shrink-0 rounded-lg border border-border/50 bg-card overflow-hidden">
          <CheckPanel
            issues={slide.issues}
            selectedIssueId={selectedIssue}
            onIssueSelect={handleIssueClick}
          />
        </div>
      </div>
    </div>
  );
}
