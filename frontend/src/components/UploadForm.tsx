import { FormEvent, useState } from "react";

interface Props {
  disabled: boolean;
  onSubmit: (formData: FormData) => Promise<void>;
}

function isXlsx(file: File | null): boolean {
  return Boolean(file && file.name.toLowerCase().endsWith(".xlsx"));
}

export function UploadForm({ disabled, onSubmit }: Props) {
  const [glfWorkbook, setGlfWorkbook] = useState<File | null>(null);
  const [rosterWorkbook, setRosterWorkbook] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [validationError, setValidationError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!isXlsx(glfWorkbook)) {
      setValidationError("Upload the GLF Assessment Workbook as an .xlsx file.");
      return;
    }
    if (!isXlsx(rosterWorkbook)) {
      setValidationError("Upload the Roster Ward Allocation Workbook as an .xlsx file.");
      return;
    }
    if (!password.trim()) {
      setValidationError("Enter the GLF workbook password.");
      return;
    }
    setValidationError("");
    const formData = new FormData();
    formData.append("glf_workbook", glfWorkbook as File);
    formData.append("roster_workbook", rosterWorkbook as File);
    formData.append("glf_password", password);
    await onSubmit(formData);
  }

  return (
    <form className="upload-panel" onSubmit={handleSubmit}>
      <label>
        <span>GLF Assessment Workbook</span>
        <input type="file" accept=".xlsx" onChange={(event) => setGlfWorkbook(event.target.files?.[0] ?? null)} />
      </label>
      <label>
        <span>Roster Ward Allocation Workbook</span>
        <input type="file" accept=".xlsx" onChange={(event) => setRosterWorkbook(event.target.files?.[0] ?? null)} />
      </label>
      <label>
        <span>GLF Workbook Password</span>
        <input
          type="password"
          value={password}
          autoComplete="current-password"
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      {validationError && <div className="form-error">{validationError}</div>}
      <button type="submit" disabled={disabled}>
        {disabled ? "Generating..." : "Generate Allocation"}
      </button>
    </form>
  );
}
