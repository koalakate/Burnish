export default function HomePage() {
  return (
    <div>
      <h2 className="font-mono text-2xl font-medium tracking-tight mb-1">
        Dashboard
      </h2>
      <p className="text-sm text-muted-foreground mb-8">
        Recent decks and quality overview
      </p>

      {/* Empty state */}
      <div className="rounded-lg border border-dashed border-border/60 p-12 text-center">
        <p className="font-mono text-4xl text-muted-foreground/30 mb-4">▦</p>
        <p className="text-sm text-muted-foreground">
          No decks yet. Upload your first presentation to get started.
        </p>
      </div>
    </div>
  );
}
