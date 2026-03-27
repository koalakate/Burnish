export default function UploadPage() {
  return (
    <div>
      <h2 className="font-mono text-2xl font-medium tracking-tight mb-1">
        Upload
      </h2>
      <p className="text-sm text-muted-foreground mb-8">
        Drop a .pptx file to check it against your brand rules
      </p>

      {/* Dropzone placeholder */}
      <div
        className="rounded-lg border-2 border-dashed border-cyan-400/30 p-16 text-center
                    hover:border-cyan-400/60 hover:bg-cyan-400/5 transition-all cursor-pointer"
      >
        <p className="font-mono text-5xl text-cyan-400/40 mb-4">↑</p>
        <p className="text-sm text-muted-foreground mb-2">
          Drag &amp; drop your .pptx here
        </p>
        <p className="text-xs text-muted-foreground/60">
          or click to browse — max 50MB
        </p>
      </div>
    </div>
  );
}
