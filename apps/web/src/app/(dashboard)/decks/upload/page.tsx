"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { UploadDropzone } from "@/components/upload-dropzone";
import { useUploadDeck, useTriggerCheck } from "@/lib/queries";

export default function UploadPage() {
  const router = useRouter();
  const uploadMutation = useUploadDeck();
  const checkMutation = useTriggerCheck();
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
        setProgress(90);

        // Auto-trigger check
        const { check_run_id } = await checkMutation.mutateAsync(deck_id);
        setProgress(100);

        clearInterval(interval);

        // Navigate to check results
        router.push(`/checks/${check_run_id}`);
      } catch {
        clearInterval(interval);
        setProgress(0);
      }
    },
    [uploadMutation, checkMutation, router]
  );

  const error =
    uploadMutation.error?.message ||
    checkMutation.error?.message ||
    null;

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
          isUploading={uploadMutation.isPending || checkMutation.isPending}
          progress={progress}
          error={error}
        />
      </div>
    </div>
  );
}
