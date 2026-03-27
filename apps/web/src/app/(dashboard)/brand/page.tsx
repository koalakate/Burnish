export default function BrandPage() {
  return (
    <div>
      <h2 className="font-mono text-2xl font-medium tracking-tight mb-1">
        Brand Rulesets
      </h2>
      <p className="text-sm text-muted-foreground mb-8">
        Define color palettes, fonts, and layout rules for your brands
      </p>

      {/* Empty state */}
      <div className="rounded-lg border border-dashed border-border/60 p-12 text-center">
        <p className="font-mono text-4xl text-muted-foreground/30 mb-4">◉</p>
        <p className="text-sm text-muted-foreground">
          No brand rulesets yet. Create your first one to start checking decks.
        </p>
      </div>
    </div>
  );
}
