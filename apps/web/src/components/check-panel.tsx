"use client";

import type { Issue, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

type CheckPanelProps = {
  issues: Issue[];
  selectedIssueId?: string | null;
  onIssueSelect?: (issue: Issue) => void;
};

const SEVERITY_ORDER: Record<Severity, number> = {
  error: 0,
  warning: 1,
  info: 2,
};

function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
        severity === "error" && "bg-severity-error/15 text-severity-error",
        severity === "warning" && "bg-severity-warning/15 text-severity-warning",
        severity === "info" && "bg-brand-400/15 text-brand-400"
      )}
    >
      {severity}
    </span>
  );
}

function RuleTypeBadge({ ruleType }: { ruleType: string }) {
  return (
    <span className="inline-flex items-center rounded bg-muted/50 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
      {ruleType}
    </span>
  );
}

function groupByEvaluator(issues: Issue[]): Record<string, Issue[]> {
  const groups: Record<string, Issue[]> = {};
  for (const issue of issues) {
    const key = issue.rule_type;
    if (!groups[key]) groups[key] = [];
    groups[key].push(issue);
  }
  return groups;
}

export function CheckPanel({
  issues,
  selectedIssueId,
  onIssueSelect,
}: CheckPanelProps) {
  const sorted = [...issues].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
  );
  const grouped = groupByEvaluator(sorted);

  const errorCount = issues.filter((i) => i.severity === "error").length;
  const warningCount = issues.filter((i) => i.severity === "warning").length;
  const infoCount = issues.filter((i) => i.severity === "info").length;

  return (
    <div className="flex flex-col h-full">
      {/* Summary header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50">
        <span className="text-sm font-medium">Issues</span>
        <div className="flex items-center gap-2 ml-auto text-xs tabular-nums">
          {errorCount > 0 && (
            <span className="text-severity-error">{errorCount} error{errorCount !== 1 ? "s" : ""}</span>
          )}
          {warningCount > 0 && (
            <span className="text-severity-warning">{warningCount} warn</span>
          )}
          {infoCount > 0 && (
            <span className="text-brand-400">{infoCount} info</span>
          )}
        </div>
      </div>

      {/* Grouped issue list */}
      <div className="flex-1 overflow-y-auto">
        {Object.entries(grouped).map(([ruleType, groupIssues]) => (
          <div key={ruleType}>
            <div className="px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider bg-muted/20 border-b border-border/30">
              {ruleType}
            </div>
            {groupIssues.map((issue) => (
              <button
                key={issue.id}
                onClick={() => onIssueSelect?.(issue)}
                className={cn(
                  "w-full text-left px-4 py-3 border-b border-border/30 transition-colors hover:bg-muted/30",
                  issue.id === selectedIssueId && "bg-muted/40 border-l-2 border-l-brand-400"
                )}
              >
                <div className="flex items-start gap-2">
                  <SeverityBadge severity={issue.severity} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground/90 leading-snug">
                      {issue.message}
                    </p>
                    {(issue.original_value || issue.expected_value) && (
                      <div className="flex items-center gap-1.5 mt-1.5 text-xs text-muted-foreground">
                        {issue.original_value && (
                          <span className="font-mono line-through opacity-60">
                            {issue.original_value}
                          </span>
                        )}
                        {issue.original_value && issue.expected_value && (
                          <span className="text-muted-foreground/40">→</span>
                        )}
                        {issue.expected_value && (
                          <span className="font-mono text-brand-400">
                            {issue.expected_value}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <RuleTypeBadge ruleType={issue.rule_type} />
                </div>
              </button>
            ))}
          </div>
        ))}

        {issues.length === 0 && (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-muted-foreground">No issues found.</p>
          </div>
        )}
      </div>
    </div>
  );
}
