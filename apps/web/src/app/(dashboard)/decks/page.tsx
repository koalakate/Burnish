import Link from "next/link";

export default function DecksPage() {
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
                     bg-cyan-400 text-slate-950 rounded-md hover:bg-cyan-300 transition-colors"
        >
          Upload Deck
        </Link>
      </div>

      {/* Empty state */}
      <div className="rounded-lg border border-dashed border-border/60 p-12 text-center">
        <p className="font-mono text-4xl text-muted-foreground/30 mb-4">▦</p>
        <p className="text-sm text-muted-foreground">
          No decks uploaded yet.
        </p>
      </div>
    </div>
  );
}
