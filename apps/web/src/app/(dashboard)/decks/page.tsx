"use client";

import Link from "next/link";
import { DeckCard } from "@/components/deck-card";
import { useDecks } from "@/lib/queries";

export default function DecksPage() {
  const { data: decks, isLoading, error } = useDecks();

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="font-mono text-2xl font-medium tracking-tight mb-1">
            Decks
          </h2>
          <p className="text-sm text-muted-foreground">
            All presentations in your organization
          </p>
        </div>
        <Link
          href="/decks/upload"
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium
                     bg-brand-400 text-slate-950 rounded-md hover:bg-brand-300 transition-colors"
        >
          Upload Deck
        </Link>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="rounded-lg border border-border/50 bg-card p-3 animate-pulse"
            >
              <div className="aspect-video rounded-md bg-muted/50 mb-3" />
              <div className="h-4 bg-muted/50 rounded w-3/4 mb-2" />
              <div className="h-3 bg-muted/30 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center">
          <p className="text-sm text-destructive">
            Failed to load decks. Please try again.
          </p>
        </div>
      )}

      {decks && decks.length === 0 && (
        <div className="rounded-lg border border-dashed border-border/60 p-12 text-center">
          <p className="font-mono text-4xl text-muted-foreground/30 mb-4">▦</p>
          <p className="text-sm text-muted-foreground">
            No decks uploaded yet.
          </p>
        </div>
      )}

      {decks && decks.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {decks.map((deck) => (
            <DeckCard key={deck.id} deck={deck} />
          ))}
        </div>
      )}
    </div>
  );
}
