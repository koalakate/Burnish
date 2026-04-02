"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { UploadDropzone } from "@/components/upload-dropzone";
import { useUploadDeck } from "@/lib/queries";

export default function UploadPage() {
  const router = useRouter();
  const uploadMutation = useUploadDeck();
  const [progress, setProgress] = useState(0);

  const handleFileAccepted = useCallback(
    async (file: File) => {
      setProgress(10);

      // Simulate progress during upload (real progress would need XHR)
      const interval = setInterval(() => {
        setProgress((p) => Math.min(p + 15, 85));
      }, 400);

      try {
        const { deck_id } = await uploadMutation.mutateAsync(file);
        setProgress(100);
        clearInterval(interval);

        // Navigate to deck detail — ingestion runs async, check can be
        // triggered once the deck status is "parsed"
        router.push(`/decks/${deck_id}`);
      } catch {
        clearInterval(interval);
        setProgress(0);
      }
    },
    [uploadMutation, router]
  );

  const error = uploadMutation.error?.message || null;

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-6rem)]">
      <div className="w-full max-w-2xl">
        <h2 className="font-mono text-2xl font-medium tracking-tight mb-1 text-center">
          Upload
        </h2>
        <p className="text-sm text-muted-foreground mb-8 text-center">
          Drop a .pptx file to check it against your brand rules
        </p>

        <UploadDropzone
          onFileAccepted={handleFileAccepted}
          isUploading={uploadMutation.isPending}
          progress={progress}
          error={error}
        />
      </div>
    </div>
  );
}
