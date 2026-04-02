"use client";

import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB
const ACCEPTED_TYPE =
  "application/vnd.openxmlformats-officedocument.presentationml.presentation";
const ACCEPTED_EXT = ".pptx";

type UploadDropzoneProps = {
  onFileAccepted: (file: File) => void;
  isUploading?: boolean;
  progress?: number;
  error?: string | null;
};

export function UploadDropzone({
  onFileAccepted,
  isUploading = false,
  progress = 0,
  error = null,
}: UploadDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback((file: File): string | null => {
    if (!file.name.toLowerCase().endsWith(ACCEPTED_EXT)) {
      return "Only .pptx files are supported";
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max 50 MB.`;
    }
    return null;
  }, []);

  const handleFile = useCallback(
    (file: File) => {
      const err = validate(file);
      if (err) {
        setValidationError(err);
        return;
      }
      setValidationError(null);
      onFileAccepted(file);
    },
    [validate, onFileAccepted]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const onChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const displayError = error || validationError;

  return (
    <div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={() => !isUploading && inputRef.current?.click()}
      className={cn(
        "relative rounded-xl border-2 border-dashed p-16 text-center transition-all cursor-pointer",
        isDragOver
          ? "border-brand-400 bg-brand-400/10 scale-[1.01]"
          : "border-brand-400/30 hover:border-brand-400/60 hover:bg-brand-400/5",
        isUploading && "pointer-events-none opacity-80"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPE}
        onChange={onChange}
        className="hidden"
      />

      {isUploading ? (
        <div className="space-y-4">
          <p className="font-mono text-4xl text-brand-400 animate-pulse">
            ↑
          </p>
          <p className="text-sm text-muted-foreground">Uploading...</p>
          <div className="mx-auto w-64 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-brand-400 rounded-full transition-all duration-300"
              style={{ width: `${Math.max(progress, 5)}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground/60">
            {progress}% complete
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="font-mono text-5xl text-brand-400/40">↑</p>
          <p className="text-sm text-muted-foreground">
            Drag &amp; drop your .pptx here
          </p>
          <p className="text-xs text-muted-foreground/60">
            or click to browse — max 50 MB
          </p>
        </div>
      )}

      {displayError && (
        <p className="mt-4 text-sm text-destructive">{displayError}</p>
      )}
    </div>
  );
}
