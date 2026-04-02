"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Correction, Severity } from "@/lib/types";
import { Check, X, Pencil } from "lucide-react";

type CorrectionCardProps = {
  correction: Correction;
  isSelected: boolean;
  onSelect: () => void;
  onAccept: (correctionId: string) => void;
  onDismiss: (correctionId: string) => void;
  onEdit: (correctionId: string, value: string) => void;
};

function SeverityDot({ severity }: { severity: Severity }) {
  return (
    <span
      className={cn(
        "block size-2 rounded-full shrink-0 mt-1",
        severity === "error" && "bg-severity-error",
        severity === "warning" && "bg-severity-warning",
        severity === "info" && "bg-brand-400"
      )}
    />
  );
}

export function CorrectionCard({
  correction,
  isSelected,
  onSelect,
  onAccept,
  onDismiss,
  onEdit,
}: CorrectionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(
    correction.expected_value ?? ""
  );

  const isDone = correction.correction_status === "accepted" || correction.correction_status === "rejected";

  const handleSaveEdit = () => {
    onEdit(correction.id, editValue);
    setIsEditing(false);
  };

  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full text-left px-4 py-3 border-b border-border/30 transition-colors",
        !isDone && "hover:bg-muted/30",
        isSelected && "bg-muted/40 border-l-2 border-l-brand-400",
        correction.correction_status === "accepted" && "opacity-60",
        correction.correction_status === "rejected" && "opacity-40"
      )}
    >
      <div className="flex items-start gap-2">
        <SeverityDot severity={correction.severity} />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-foreground/90 leading-snug">
            {correction.message}
          </p>

          {/* Change description */}
          {(correction.original_value || correction.expected_value) && !isEditing && (
            <div className="flex items-center gap-1.5 mt-1.5 text-xs text-muted-foreground">
              {correction.original_value && (
                <span className="font-mono line-through opacity-60">
                  {correction.original_value}
                </span>
              )}
              {correction.original_value && correction.expected_value && (
                <span className="text-muted-foreground/40">→</span>
              )}
              {correction.expected_value && (
                <span className="font-mono text-brand-400">
                  {correction.correction_status === "rejected"
                    ? correction.expected_value
                    : editValue || correction.expected_value}
                </span>
              )}
            </div>
          )}

          {/* Inline editor (Priya's edit-in-place) */}
          {isEditing && (
            <div className="mt-2 flex gap-1.5" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="flex-1 h-7 px-2 text-xs font-mono rounded border border-border bg-background focus:outline-none focus:border-brand-400"
                autoFocus
              />
              <Button
                size="icon-xs"
                variant="default"
                onClick={(e) => {
                  e.stopPropagation();
                  handleSaveEdit();
                }}
              >
                <Check className="size-3" />
              </Button>
              <Button
                size="icon-xs"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsEditing(false);
                  setEditValue(correction.expected_value ?? "");
                }}
              >
                <X className="size-3" />
              </Button>
            </div>
          )}

          {/* Status badge */}
          {correction.correction_status === "accepted" && (
            <span className="inline-flex items-center gap-1 mt-1.5 text-[10px] font-medium text-dqs-good">
              <Check className="size-3" /> Accepted
            </span>
          )}
          {correction.correction_status === "rejected" && (
            <span className="inline-flex items-center gap-1 mt-1.5 text-[10px] font-medium text-muted-foreground">
              <X className="size-3" /> Dismissed
            </span>
          )}

          {/* Action buttons */}
          {correction.correction_status === "pending" && !isEditing && (
            <div
              className="flex items-center gap-1 mt-2"
              onClick={(e) => e.stopPropagation()}
            >
              <Button
                size="xs"
                variant="default"
                onClick={(e) => {
                  e.stopPropagation();
                  onAccept(correction.id);
                }}
              >
                <Check className="size-3" data-icon="inline-start" />
                Accept
              </Button>
              <Button
                size="xs"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss(correction.id);
                }}
              >
                <X className="size-3" data-icon="inline-start" />
                Dismiss
              </Button>
              {correction.expected_value && (
                <Button
                  size="xs"
                  variant="ghost"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditing(true);
                  }}
                >
                  <Pencil className="size-3" data-icon="inline-start" />
                  Edit
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
