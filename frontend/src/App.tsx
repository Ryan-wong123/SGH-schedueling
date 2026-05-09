import { useState } from "react";
import { generateAllocation, workbookDownloadUrl } from "./api/client";
import { ErrorMessage } from "./components/ErrorMessage";
import { ResultsSummary } from "./components/ResultsSummary";
import { ResultsTable } from "./components/ResultsTable";
import { UploadForm } from "./components/UploadForm";
import type { GenerateAllocationResponse } from "./types/allocation";
import "./styles/app.css";

export default function App() {
  const [result, setResult] = useState<GenerateAllocationResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleGenerate(formData: FormData) {
    setLoading(true);
    setError("");
    setResult(null);
    try {
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
              <ResultsSummary summary={result.summary} />
              <a className="download-button" href={workbookDownloadUrl(result.download_id)}>
                Download workbook
              </a>
            </div>
            <ResultsTable records={result.records} />
          </section>
        )}
      </section>
    </main>
  );
}
