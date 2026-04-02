"use client";

import { use, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useDeck, useTriggerCheck } from "@/lib/queries";
import { Button } from "@/components/ui/button";
import { Loader2, FileCheck } from "lucide-react";

export default function DeckDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: deckId } = use(params);
  const router = useRouter();
  const { data: deck, isLoading, error } = useDeck(deckId);
  const triggerCheck = useTriggerCheck();

  // Auto-trigger a check once the deck is parsed
  const hasTriggeredCheck = useRef(false);
  useEffect(() => {
    if (deck?.status === "parsed" && !hasTriggeredCheck.current) {
      hasTriggeredCheck.current = true;
      triggerCheck.mutate(deckId, {
        onSuccess: (data) => {
          router.push(`/checks/${data.check_run_id}`);
        },
      });
    }
  }, [deck?.status, deckId, triggerCheck, router]);

  // If there's already a check running or complete, navigate there
  // (handled by the trigger response above)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-6rem)]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !deck) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-6rem)] gap-4">
        <p className="text-sm text-destructive">
          {error?.message || "Deck not found"}
        </p>
        <Link href="/decks" className="text-sm text-muted-foreground hover:text-foreground">
          Back to library
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-12 space-y-6">
      <div className="flex items-center gap-2 text-sm">
        <Link
          href="/decks"
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          Library
        </Link>
        <span className="text-muted-foreground/40">/</span>
        <span className="text-foreground">{deck.name}</span>
      </div>

      <div className="rounded-lg border p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-mono text-xl font-medium tracking-tight">
            {deck.name}
          </h2>
          <span className="text-xs font-mono px-2 py-1 rounded bg-muted text-muted-foreground">
            {deck.status}
          </span>
        </div>

        <div className="text-sm text-muted-foreground space-y-1">
          <p>{deck.slide_count} slides</p>
          <p>Uploaded {new Date(deck.created_at).toLocaleDateString()}</p>
        </div>

        {deck.status === "uploading" || deck.status === "parsing" ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Processing deck...</span>
          </div>
        ) : deck.status === "parsed" ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Starting check...</span>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              triggerCheck.mutate(deckId, {
                onSuccess: (data) => router.push(`/checks/${data.check_run_id}`),
              })
            }
            disabled={triggerCheck.isPending}
          >
            <FileCheck className="h-4 w-4 mr-1" />
            Run Check
          </Button>
        )}
      </div>
    </div>
  );
}
