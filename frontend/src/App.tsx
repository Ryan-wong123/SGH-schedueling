import { useState } from "react";
import { generateAllocation, workbookDownloadUrl } from "./api/client";
import { ErrorMessage } from "./components/ErrorMessage";
import { ResultsSummary } from "./components/ResultsSummary";
import { ResultsTable } from "./components/ResultsTable";
import { UploadForm } from "./components/UploadForm";
import type { AllocationRecord, GenerateAllocationResponse, ResultsFilter } from "./types/allocation";
import "./styles/app.css";

function recordMatchesFilter(record: AllocationRecord, filter: ResultsFilter) {
  if (filter === "allocated") {
    return record.status === "Allocated";
  }
  if (filter === "unallocated") {
    return record.status === "Unallocated";
  }
  return record.status.startsWith("Skipped");
}

export default function App() {
  const [result, setResult] = useState<GenerateAllocationResponse | null>(null);
  const [resultsFilter, setResultsFilter] = useState<ResultsFilter>("allocated");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleGenerate(formData: FormData) {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResultsFilter("allocated");
      setResult(await generateAllocation(formData));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected processing error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <div className="masthead">
          <div>
            <p className="eyebrow">GLF Assessment Scheduler</p>
            <h1>Generate assessment allocations</h1>
          </div>
          <div className="status-card">{loading ? "Generating allocation, please wait..." : "Ready"}</div>
        </div>

        <UploadForm disabled={loading} onSubmit={handleGenerate} />
        <ErrorMessage message={error} />

        {result && (
          <section className="results">
            <div className="results-top">
              <ResultsSummary activeFilter={resultsFilter} summary={result.summary} onFilterChange={setResultsFilter} />
              <a className="download-button" href={workbookDownloadUrl(result.download_id)}>
                Download workbook
              </a>
            </div>
            <ResultsTable records={result.records.filter((record) => recordMatchesFilter(record, resultsFilter))} />
          </section>
        )}
      </section>
    </main>
  );
}
