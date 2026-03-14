/**
 * Utility for normalizing backend finding responses.
 *
 * The backend returns snake_case fields (confidence_score, framework_control, etc.)
 * while the frontend Finding type uses camelCase. This module provides a single
 * normalization function used wherever findings are fetched from the API.
 */

import type { Finding, FindingType, Severity } from '@/types/api';

/**
 * Map a raw backend FindingResponse (snake_case) to the camelCase Finding shape
 * expected by FindingCard, FindingsList, and FindingsSummary.
 *
 * Backend fields that differ from the frontend type:
 *   analysis_run_id   -> runId
 *   document_id       -> documentId
 *   framework_control -> controlId (first segment) + controlName (remainder)
 *   finding_type      -> findingType  (may be absent; defaults to 'gap')
 *   confidence_score  -> confidenceScore
 *   remediation       -> recommendation
 *   page_number       -> pageReferences (single number -> single-element array)
 *   created_at        -> createdAt
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeFinding(raw: any): Finding {
  // framework_control may look like "CC6.1 - Logical Access Controls"
  // Split on first " - " to get controlId and controlName separately.
  const frameworkControl: string = raw.framework_control ?? raw.controlId ?? '';
  const separatorIdx = frameworkControl.indexOf(' - ');
  const controlId =
    separatorIdx !== -1 ? frameworkControl.slice(0, separatorIdx) : frameworkControl;
  const controlName =
    separatorIdx !== -1 ? frameworkControl.slice(separatorIdx + 3) : (raw.controlName ?? '');

  return {
    id: raw.id ?? '',
    runId: raw.analysis_run_id ?? raw.runId ?? '',
    documentId: raw.document_id ?? raw.documentId ?? '',
    controlId,
    controlName,
    framework: raw.framework ?? '',
    findingType: (raw.finding_type ?? raw.findingType ?? 'gap') as FindingType,
    severity: (raw.severity ?? 'info') as Severity,
    title: raw.title ?? '',
    description: raw.description ?? '',
    evidence: raw.evidence ?? undefined,
    recommendation: raw.remediation ?? raw.recommendation ?? undefined,
    pageReferences:
      raw.page_number != null
        ? [raw.page_number as number]
        : (raw.pageReferences ?? []),
    citations: raw.citations ?? [],
    confidenceScore: raw.confidence_score ?? raw.confidenceScore ?? 0,
    status: raw.status ?? 'open',
    createdAt: raw.created_at ?? raw.createdAt ?? new Date().toISOString(),
  };
}
