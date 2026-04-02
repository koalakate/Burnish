export type Severity = "error" | "warning" | "info";

export type CheckStatus = "queued" | "running" | "complete" | "failed";

export type CorrectionStatus = "pending" | "accepted" | "rejected" | "edited";

export interface Deck {
  id: string;
  name: string;
  status: string;
  source_type: string;
  slide_count: number;
  created_at: string;
  updated_at: string;
}

export interface CheckRun {
  id: string;
  deck_id: string;
  status: CheckStatus;
  dqs_overall: number | null;
  issue_count_error: number;
  issue_count_warning: number;
  issue_count_info: number;
  created_at: string;
}

export interface Issue {
  id: string;
  rule_type: string;
  severity: Severity;
  message: string;
  element_id: string | null;
  element_bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
  original_value: string | null;
  expected_value: string | null;
  correction_status: CorrectionStatus | null;
}

export interface BrandRuleset {
  id: string;
  name: string;
  version: number;
  is_active: boolean;
  rules: Record<string, unknown>;
}

export interface SlideCheckResult {
  id: string;
  slide_index: number;
  dqs_slide: number;
  thumbnail_ref: string;
  issues: Issue[];
}

export interface CheckRunDetail extends CheckRun {
  started_at: string | null;
  completed_at: string | null;
  slides: SlideSummary[];
}

export interface SlideSummary {
  slide_index: number;
  dqs_slide: number;
  thumbnail_url: string | null;
}

export interface SlideDetail {
  slide_index: number;
  dqs_slide: number;
  thumbnail_url: string | null;
  issues: Issue[];
}

export interface Correction {
  id: string;
  rule_type: string;
  severity: Severity;
  message: string;
  element_id: string | null;
  element_bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
  original_value: string | null;
  expected_value: string | null;
  correction_status: CorrectionStatus | null;
}

export interface SlideCorrections {
  slide_index: number;
  corrections: Correction[];
}

export interface CorrectionsResponse {
  check_run_id: string;
  slides: SlideCorrections[];
  total: number;
}

export interface ExportResponse {
  check_run_id: string;
  download_url: string;
  dqs_after: number | null;
}
