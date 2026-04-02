"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Stage, Layer, Image as KonvaImage } from "react-konva";
import { IssueOverlay } from "@/components/issue-overlay";
import type { Issue } from "@/lib/types";

type SlidePreviewProps = {
  thumbnailUrl: string | null;
  issues?: Issue[];
  selectedIssueId?: string | null;
  onIssueClick?: (issue: Issue) => void;
  className?: string;
};

const SLIDE_WIDTH = 960;
const SLIDE_HEIGHT = 540;

export function SlidePreview({
  thumbnailUrl,
  issues = [],
  selectedIssueId,
  onIssueClick,
  className,
}: SlidePreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: SLIDE_WIDTH, height: SLIDE_HEIGHT });
  const [image, setImage] = useState<HTMLImageElement | null>(null);

  const updateDimensions = useCallback(() => {
    if (!containerRef.current) return;
    const containerWidth = containerRef.current.clientWidth;
    const width = containerWidth;
    const height = width / (SLIDE_WIDTH / SLIDE_HEIGHT);
    setDimensions({ width, height });
  }, []);

  useEffect(() => {
    updateDimensions();
    const observer = new ResizeObserver(updateDimensions);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [updateDimensions]);

  useEffect(() => {
    if (!thumbnailUrl) return;
    const img = new window.Image();
    img.crossOrigin = "anonymous";
    img.src = thumbnailUrl;
    img.onload = () => setImage(img);
    return () => {
      img.onload = null;
      setImage(null);
    };
  }, [thumbnailUrl]);

  const scaleX = dimensions.width / SLIDE_WIDTH;
  const scaleY = dimensions.height / SLIDE_HEIGHT;

  return (
    <div ref={containerRef} className={className}>
      <Stage width={dimensions.width} height={dimensions.height}>
        <Layer>
          {image ? (
            <KonvaImage
              image={image}
              width={dimensions.width}
              height={dimensions.height}
            />
          ) : (
            <></>
          )}
          <IssueOverlay
            issues={issues}
            selectedIssueId={selectedIssueId}
            onIssueClick={onIssueClick}
            scaleX={scaleX}
            scaleY={scaleY}
          />
        </Layer>
      </Stage>
      {!thumbnailUrl && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/30 rounded-lg">
          <span className="font-mono text-4xl text-muted-foreground/20">▦</span>
        </div>
      )}
    </div>
  );
}
