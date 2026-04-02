"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Stage, Layer, Image as KonvaImage, Rect, Group } from "react-konva";
import type { Correction } from "@/lib/types";

type CorrectionViewProps = {
  originalThumbnailUrl: string | null;
  correctedThumbnailUrl: string | null;
  corrections: Correction[];
  selectedCorrectionId?: string | null;
  onCorrectionClick?: (correction: Correction) => void;
};

const SLIDE_WIDTH = 960;
const SLIDE_HEIGHT = 540;

function useImage(url: string | null) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);

  useEffect(() => {
    if (!url) return;
    const img = new window.Image();
    img.crossOrigin = "anonymous";
    img.src = url;
    img.onload = () => setImage(img);
    return () => {
      img.onload = null;
      setImage(null);
    };
  }, [url]);

  return image;
}

function SlideCanvas({
  image,
  dimensions,
  corrections,
  selectedCorrectionId,
  onCorrectionClick,
  showGlow,
}: {
  image: HTMLImageElement | null;
  dimensions: { width: number; height: number };
  corrections: Correction[];
  selectedCorrectionId?: string | null;
  onCorrectionClick?: (correction: Correction) => void;
  showGlow: boolean;
}) {
  const scaleX = dimensions.width / SLIDE_WIDTH;
  const scaleY = dimensions.height / SLIDE_HEIGHT;

  return (
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
        {showGlow &&
          corrections
            .filter((c) => c.element_bbox && c.correction_status !== "rejected")
            .map((correction) => {
              const bbox = correction.element_bbox!;
              const isSelected = correction.id === selectedCorrectionId;
              return (
                <Group
                  key={correction.id}
                  onClick={() => onCorrectionClick?.(correction)}
                  onTap={() => onCorrectionClick?.(correction)}
                >
                  <Rect
                    x={bbox.x * scaleX - 2}
                    y={bbox.y * scaleY - 2}
                    width={bbox.width * scaleX + 4}
                    height={bbox.height * scaleY + 4}
                    stroke="#22d3ee"
                    strokeWidth={isSelected ? 3 : 2}
                    fill={isSelected ? "rgba(34,211,238,0.12)" : "rgba(34,211,238,0.06)"}
                    cornerRadius={3}
                    shadowColor="#22d3ee"
                    shadowBlur={isSelected ? 12 : 6}
                    shadowOpacity={0.4}
                  />
                </Group>
              );
            })}
      </Layer>
    </Stage>
  );
}

export function CorrectionView({
  originalThumbnailUrl,
  correctedThumbnailUrl,
  corrections,
  selectedCorrectionId,
  onCorrectionClick,
}: CorrectionViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({
    width: SLIDE_WIDTH / 2,
    height: SLIDE_HEIGHT / 2,
  });

  const originalImage = useImage(originalThumbnailUrl);
  const correctedImage = useImage(correctedThumbnailUrl);

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

  return (
    <div className="grid grid-cols-2 gap-3">
      {/* Original */}
      <div>
        <div className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
          Original
        </div>
        <div
          ref={containerRef}
          className="relative rounded-lg overflow-hidden border border-border/50"
        >
          <SlideCanvas
            image={originalImage}
            dimensions={dimensions}
            corrections={[]}
            showGlow={false}
          />
          {!originalThumbnailUrl && (
            <div className="absolute inset-0 flex items-center justify-center bg-muted/30">
              <span className="font-mono text-4xl text-muted-foreground/20">
                ▦
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Corrected */}
      <div>
        <div className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
          Corrected
        </div>
        <div className="relative rounded-lg overflow-hidden border border-brand-400/30">
          <SlideCanvas
            image={correctedImage}
            dimensions={dimensions}
            corrections={corrections}
            selectedCorrectionId={selectedCorrectionId}
            onCorrectionClick={onCorrectionClick}
            showGlow={true}
          />
          {!correctedThumbnailUrl && (
            <div className="absolute inset-0 flex items-center justify-center bg-muted/30">
              <span className="font-mono text-4xl text-muted-foreground/20">
                ▦
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
