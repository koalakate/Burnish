"use client";

import Image from "next/image";
import Link from "next/link";
import type { Deck } from "@/lib/types";
import { cn } from "@/lib/utils";
import { DqsBadge } from "@/components/dqs-badge";

type DeckCardProps = {
  deck: Deck;
  dqs?: number | null;
  thumbnailUrl?: string | null;
};

function StatusDot({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-block size-2 rounded-full",
        status === "parsing" && "bg-severity-warning animate-pulse",
        status === "checking" && "bg-brand-400 animate-pulse",
        status === "ready" && "bg-dqs-good",
        status === "error" && "bg-destructive"
      )}
    />
  );
}

export function DeckCard({
  deck,
  dqs = null,
  thumbnailUrl = null,
}: DeckCardProps) {
  const status = deck.status === "parsed" ? "ready" : deck.status;
  const formattedDate = new Date(deck.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  return (
    <Link
      href={`/decks/${deck.id}`}
      className="group block rounded-lg border border-border/50 bg-card p-3 transition-all hover:border-border hover:shadow-md"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video rounded-md bg-muted/50 mb-3 overflow-hidden flex items-center justify-center">
        {thumbnailUrl ? (
          <Image
            src={thumbnailUrl}
            alt={`${deck.name} thumbnail`}
            fill
            className="object-cover"
          />
        ) : (
          <span className="font-mono text-2xl text-muted-foreground/20">
            ▦
          </span>
        )}
      </div>

      {/* Info */}
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-medium truncate group-hover:text-foreground text-foreground/90">
            {deck.name}
          </h3>
          {dqs != null && <DqsBadge score={dqs} size="sm" />}
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <StatusDot status={status} />
          <span className="capitalize">{status}</span>
          <span className="text-muted-foreground/40">·</span>
          <span>{formattedDate}</span>
          <span className="text-muted-foreground/40">·</span>
          <span>
            {deck.slide_count} slide{deck.slide_count !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </Link>
  );
}
