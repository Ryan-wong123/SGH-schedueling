import type { AllocationSummary, ResultsFilter } from "../types/allocation";

interface Props {
  activeFilter: ResultsFilter;
  summary: AllocationSummary;
  onFilterChange: (filter: ResultsFilter) => void;
}

const FILTER_TABS: Array<{ filter: ResultsFilter; label: string; countKey: keyof AllocationSummary }> = [
  { filter: "allocated", label: "Allocated", countKey: "allocated" },
  { filter: "unallocated", label: "Unallocated", countKey: "unallocated" },
  { filter: "skipped", label: "Skipped", countKey: "skipped" },
];

export function ResultsSummary({ activeFilter, summary, onFilterChange }: Props) {
  return (
    <div className="summary-tabs" role="tablist" aria-label="Allocation result filters">
      {FILTER_TABS.map((tab) => (
        <button
          aria-selected={activeFilter === tab.filter}
          className="summary-tab"
          key={tab.filter}
          onClick={() => onFilterChange(tab.filter)}
          role="tab"
          type="button"
        >
          <span>{tab.label}</span>
          <strong>{summary[tab.countKey]}</strong>
        </button>
      ))}
    </div>
  );
}
