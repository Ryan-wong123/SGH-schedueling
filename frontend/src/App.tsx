import { useMemo, useState } from "react";
import { generateAllocation, previewWorkbookDownloadUrl, workbookDownloadUrl } from "./api/client";
import { ErrorMessage } from "./components/ErrorMessage";
import { ResultsTable } from "./components/ResultsTable";
import { UploadForm } from "./components/UploadForm";
import type { GenerateAllocationResponse } from "./types/allocation";
import "./styles/app.css";

export default function App() {
  const [result, setResult] = useState<GenerateAllocationResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dateFilter, setDateFilter] = useState("");

  async function handleGenerate(formData: FormData) {
    setLoading(true);
    setError("");
    setResult(null);
    setDateFilter("");
    try {
      setResult(await generateAllocation(formData));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected processing error.");
    } finally {
      setLoading(false);
    }
  }

  const allocatedRecords = useMemo(
    () => result?.records.filter((record) => record.status === "Allocated") ?? [],
    [result],
  );

  const allocationDates = useMemo(
    () => Array.from(new Set(allocatedRecords.map((record) => record.date).filter(Boolean))).sort(),
    [allocatedRecords],
  );

  const filteredRecords = useMemo(
    () => (dateFilter ? allocatedRecords.filter((record) => record.date === dateFilter) : allocatedRecords),
    [allocatedRecords, dateFilter],
  );

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
              <div className="allocated-summary">
                <span>Allocated</span>
                <strong>{result.summary.allocated}</strong>
              </div>
              <a className="download-button" href={workbookDownloadUrl(result.download_id)}>
                Download full GLF workbook
              </a>
              <a className="download-button secondary" href={previewWorkbookDownloadUrl(result.preview_download_id)}>
                Download new allocation
              </a>
            </div>
            <div className="results-filter">
              <label>
                <span>Filter by date</span>
                <select value={dateFilter} onChange={(event) => setDateFilter(event.target.value)}>
                  <option value="">All dates</option>
                  {allocationDates.map((date) => (
                    <option key={date} value={date}>
                      {date}
                    </option>
                  ))}
                </select>
              </label>
              <span>
                Showing {filteredRecords.length} of {allocatedRecords.length} allocated records
              </span>
            </div>
            <ResultsTable records={filteredRecords} />
          </section>
        )}
      </section>
    </main>
  );
}
