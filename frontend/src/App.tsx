import { useMemo, useState } from "react";
import { generateAllocation, previewWorkbookDownloadUrl, workbookDownloadUrl } from "./api/client";
import { ErrorMessage } from "./components/ErrorMessage";
import { ResultsTable } from "./components/ResultsTable";
import { UploadForm } from "./components/UploadForm";
import type { GenerateAllocationResponse } from "./types/allocation";
import "./styles/app.css";

function parseDisplayDate(dateText: string): number {
  const [day, month, year] = dateText.split("/").map(Number);
  if (!day || !month || year === undefined) {
    return Number.NaN;
  }
  const fullYear = year < 100 ? 2000 + year : year;
  return new Date(fullYear, month - 1, day).getTime();
}

function isDateInRange(dateText: string, startDate: string, endDate: string): boolean {
  const current = parseDisplayDate(dateText);
  const start = startDate ? parseDisplayDate(startDate) : Number.NEGATIVE_INFINITY;
  const end = endDate ? parseDisplayDate(endDate) : Number.POSITIVE_INFINITY;
  const lower = Math.min(start, end);
  const upper = Math.max(start, end);
  if (Number.isNaN(current)) {
    return false;
  }
  return current >= lower && current <= upper;
}

function sortDisplayDates(dates: string[]): string[] {
  return [...dates].sort((left, right) => parseDisplayDate(left) - parseDisplayDate(right) || left.localeCompare(right));
}

export default function App() {
  const [result, setResult] = useState<GenerateAllocationResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  async function handleGenerate(formData: FormData) {
    setLoading(true);
    setError("");
    setResult(null);
    setStartDate("");
    setEndDate("");
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

  const dateOptions = useMemo(
    () =>
      sortDisplayDates(
        Array.from(
          new Set([
            ...allocatedRecords.map((record) => record.date).filter(Boolean),
            ...Object.keys(result?.roster.availableAssessorsByDate ?? {}),
          ]),
        ),
      ),
    [allocatedRecords, result],
  );

  const filteredRecords = useMemo(
    () =>
      startDate || endDate
        ? allocatedRecords.filter((record) => isDateInRange(record.date, startDate, endDate))
        : allocatedRecords,
    [allocatedRecords, endDate, startDate],
  );

  const unallocatedRosteredAssessors = useMemo(() => {
    if (!result) {
      return [];
    }
    const rosteredInRange = new Set<string>();
    const allocatedInRange = new Set(filteredRecords.map((record) => record.assignedAssessor).filter(Boolean));
    for (const [date, assessors] of Object.entries(result.roster.availableAssessorsByDate)) {
      if (!startDate && !endDate) {
        assessors.forEach((assessor) => rosteredInRange.add(assessor));
      } else if (isDateInRange(date, startDate, endDate)) {
        assessors.forEach((assessor) => rosteredInRange.add(assessor));
      }
    }
    return Array.from(rosteredInRange)
      .filter((assessor) => !allocatedInRange.has(assessor))
      .sort((left, right) => left.localeCompare(right));
  }, [endDate, filteredRecords, result, startDate]);

  const dateRangeLabel = useMemo(
    () => (startDate || endDate ? `${startDate || "Earliest"} to ${endDate || "Latest"}` : "all dates"),
    [endDate, startDate],
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
                <span>Start date</span>
                <select value={startDate} onChange={(event) => setStartDate(event.target.value)}>
                  <option value="">Earliest</option>
                  {dateOptions.map((date) => (
                    <option key={date} value={date}>
                      {date}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>End date</span>
                <select value={endDate} onChange={(event) => setEndDate(event.target.value)}>
                  <option value="">Latest</option>
                  {dateOptions.map((date) => (
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
            <div className="unallocated-assessors-panel">
              <div>
                <span>Available, not allocated</span>
                <strong>{unallocatedRosteredAssessors.length}</strong>
                <p>Assessors rostered as GLF but not assigned any assessee for {dateRangeLabel}.</p>
              </div>
              {unallocatedRosteredAssessors.length > 0 ? (
                <ul>
                  {unallocatedRosteredAssessors.map((assessor) => (
                    <li key={assessor}>{assessor}</li>
                  ))}
                </ul>
              ) : (
                <p>Every rostered GLF assessor has at least one allocation in this range.</p>
              )}
            </div>
            <ResultsTable records={filteredRecords} />
          </section>
        )}
      </section>
    </main>
  );
}
