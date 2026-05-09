import type { AllocationSummary } from "../types/allocation";

interface Props {
  summary: AllocationSummary;
}

export function ResultsSummary({ summary }: Props) {
  return (
    <div className="summary-grid">
      <div>
        <span>Allocated</span>
        <strong>{summary.allocated}</strong>
      </div>
      <div>
        <span>Unallocated</span>
        <strong>{summary.unallocated}</strong>
      </div>
      <div>
        <span>Skipped</span>
        <strong>{summary.skipped}</strong>
      </div>
    </div>
  );
}
