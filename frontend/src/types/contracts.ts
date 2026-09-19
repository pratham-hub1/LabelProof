// Data Contracts (FROZEN v1.0)
// Using exact snake_case fields as defined in CONTRACTS.md

export type ScanStatus = 'PENDING' | 'PROCESSING' | 'DONE' | 'NEEDS_REVIEW' | 'FAILED';
export type RuleResultStatus = 'PASS' | 'FAIL' | 'NA' | 'NEEDS_REVIEW';
export type SourceType = 'photo' | 'pdf';
export type Language = 'en' | 'hi' | 'mixed' | 'unknown';
export type NetQuantityUnit = 'g' | 'kg' | 'ml' | 'l' | 'pcs';

// 1. Extraction JSON Types
export interface ParsedNetQuantity {
  value: number;
  unit: string;
}

export interface ParsedMrp {
  value: number;
  currency: 'INR';
}

export interface ParsedMfgDate {
  month: number;
  year: number;
}

export interface ParsedConsumerCare {
  phone: string | null;
  email: string | null;
}

export interface FieldBase<T> {
  raw: string | null;
  parsed: T | null;
  confidence: number;
  box: [number, number, number, number] | null; // [x1, y1, x2, y2]
}

export interface ExtractionFields {
  manufacturer_name: FieldBase<null>;
  manufacturer_address: FieldBase<null>;
  generic_name: FieldBase<null>;
  net_quantity: FieldBase<ParsedNetQuantity>;
  mrp: FieldBase<ParsedMrp>;
  mfg_date: FieldBase<ParsedMfgDate>;
  consumer_care: FieldBase<ParsedConsumerCare>;
  brand_guess?: string | null; // From CONTRACTS.md: exactly as printed, or null. Always null for parsed. Wait, the extraction JSON example doesn't have it as FieldBase, it's just in the field rules. Let's make it FieldBase<null> but it's optional. Actually, the example in 1. Extraction JSON doesn't list it, but "brand_guess: exactly as printed, or null". Let's omit or type loosely.
}

export interface ExtractionImage {
  width: number;
  height: number;
}

export interface ExtractionJson {
  schema_version: string;
  source_type: SourceType;
  image: ExtractionImage;
  language: Language;
  fields: ExtractionFields;
}

// 2. Scan Record Types
export interface ScanInput {
  filename: string;
  content_type: string;
  source_type: SourceType;
  label_width_mm: number | null;
  s3_key: string;
  size_bytes: number;
}

export interface ScanProduct {
  brand_guess: string | null;
  generic_name: string | null;
}

export interface ScanSummary {
  pass: number;
  fail: number;
  na: number;
  needs_review: number;
  found_declarations: number | null;
  exempt: number | null;
}

export interface ScanMeasurement {
  measured_mm: number | null;
  sigma_mm: number | null;
  required_mm: number | null;
  pdp_area_cm2: number | null;
  area_uncertainty_cm2: number | null;
  pack_class: string | null;
  method: 'calibrated_photo' | 'pdf_exact';
}

export interface RuleResult {
  rule_id: string;
  name: string;
  citation: string;
  status: RuleResultStatus;
  evidence: string | null;
  fix: string | null;
  box: [number, number, number, number] | null;
  measurement: ScanMeasurement | null;
}

export interface ScanArtifacts {
  annotated_image: string | null;
  report_pdf: string | null;
  report_json: string | null;
  report_csv: string | null;
  display_image: string | null;
}

export interface ScanExemption {
  applied: boolean;
  citation: string | null;
  reason: string | null;
}

export interface ScanError {
  code: string;
  message: string;
}

export interface ScanRecord {
  scan_id: string;
  status: ScanStatus;
  created_at: string;
  updated_at: string;
  input: ScanInput;
  product: ScanProduct | null;
  extraction: ExtractionJson | null;
  summary: ScanSummary | null;
  results: RuleResult[] | null;
  artifacts: ScanArtifacts | null;
  exemption: ScanExemption | null;
  error: ScanError | null;
}

// 3. API Types
export interface UploadRequest {
  filename: string;
  content_type: string;
  label_width_mm?: number;
}

export interface UploadResponse {
  scan_id: string;
  upload_url: string;
  expires_in: number;
}

export interface ScanListResponse {
  items: ScanRecord[];
  last_key: string | null;
}

export interface RuleStats {
  pass: number;
  fail: number;
  na: number;
  needs_review: number;
}

export interface StatsResponse {
  total_scans: number;
  overall: RuleStats;
  by_rule: Record<string, RuleStats>;
  most_failed_rules: Array<{ rule_id: string; count: number }>;
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
  };
}
