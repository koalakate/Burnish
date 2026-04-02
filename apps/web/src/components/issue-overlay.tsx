"use client";

import { Rect, Group, Text } from "react-konva";
import type { Issue } from "@/lib/types";

type IssueOverlayProps = {
  issues: Issue[];
  selectedIssueId?: string | null;
  onIssueClick?: (issue: Issue) => void;
  scaleX: number;
  scaleY: number;
};

const SEVERITY_COLORS: Record<string, string> = {
  error: "#ef4444",
  warning: "#eab308",
  info: "#06b6d4",
};

const SEVERITY_FILL: Record<string, string> = {
  error: "rgba(239,68,68,0.08)",
  warning: "rgba(234,179,8,0.08)",
  info: "rgba(6,182,212,0.08)",
};

export function IssueOverlay({
  issues,
  selectedIssueId,
  onIssueClick,
  scaleX,
  scaleY,
}: IssueOverlayProps) {
  return (
    <>
      {issues
        .filter((issue) => issue.element_bbox)
        .map((issue) => {
          const bbox = issue.element_bbox!;
          const isSelected = issue.id === selectedIssueId;
          const color = SEVERITY_COLORS[issue.severity] ?? SEVERITY_COLORS.info;
          const fill = SEVERITY_FILL[issue.severity] ?? SEVERITY_FILL.info;

          return (
            <Group
              key={issue.id}
              onClick={() => onIssueClick?.(issue)}
              onTap={() => onIssueClick?.(issue)}
            >
              <Rect
                x={bbox.x * scaleX}
                y={bbox.y * scaleY}
                width={bbox.width * scaleX}
                height={bbox.height * scaleY}
                stroke={color}
                strokeWidth={isSelected ? 3 : 1.5}
                fill={isSelected ? fill : "transparent"}
                cornerRadius={2}
                dash={isSelected ? undefined : [4, 4]}
              />
              {isSelected && (
                <Text
                  x={bbox.x * scaleX}
                  y={bbox.y * scaleY - 18}
                  text={issue.severity.toUpperCase()}
                  fontSize={10}
                  fontFamily="monospace"
                  fill={color}
                  padding={2}
                />
              )}
            </Group>
          );
        })}
    </>
  );
}
