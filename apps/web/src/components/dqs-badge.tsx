"use client";

import { cn } from "@/lib/utils";

type DqsBadgeProps = {
  score: number;
  size?: "sm" | "lg";
};

export function DqsBadge({ score, size = "sm" }: DqsBadgeProps) {
  const rounded = Math.round(score);

  if (size === "lg") {
    const circumference = 2 * Math.PI * 40;
    const offset = circumference - (rounded / 100) * circumference;

    return (
      <div className="relative inline-flex items-center justify-center">
        <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            strokeWidth="6"
            className="stroke-muted/30"
          />
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={cn(
              "transition-all duration-500",
              rounded >= 80 && "stroke-dqs-good",
              rounded >= 60 && rounded < 80 && "stroke-dqs-moderate",
              rounded < 60 && "stroke-dqs-poor"
            )}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={cn(
              "font-mono text-3xl font-bold tabular-nums",
              rounded >= 80 && "text-dqs-good",
              rounded >= 60 && rounded < 80 && "text-dqs-moderate",
              rounded < 60 && "text-dqs-poor"
            )}
          >
            {rounded}
          </span>
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
            DQS
          </span>
        </div>
      </div>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums",
        rounded >= 80 && "bg-dqs-good/15 text-dqs-good",
        rounded >= 60 && rounded < 80 && "bg-dqs-moderate/15 text-dqs-moderate",
        rounded < 60 && "bg-dqs-poor/15 text-dqs-poor"
      )}
    >
      {rounded}
    </span>
  );
}
