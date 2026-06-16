# ARCHITECTURE.md

## 1. System Overview

The GLF Assessment Scheduler is a web application that processes two Excel files, generates a new allocation worksheet inside the GLF Assessment Workbook, and produces a separate new-allocation workbook that matches the website preview output.

The system has two main parts:

1. **Frontend** — React TypeScript application for uploading files, entering the password, previewing results, and downloading the generated workbooks.
2. **Backend** — FastAPI application for reading Excel files, parsing workbook data, running allocation logic, and returning the generated workbooks.

Both parts support two downloadable artifacts after generation: the full updated GLF workbook and a separate new-allocation workbook based on the website preview rows.

---

## 2. Architecture Diagram

```text
User Browser
   |
   | upload GLF workbook + roster workbook + password
   v
React Frontend
   |
   | multipart/form-data
   v
FastAPI Backend
   |
   +--> Password-protected GLF reader
   |
   +--> Roster parser
   |
   +--> GLF progress parser
   |
   +--> Allocation engine
   |
   +--> Workbook writer
   |
   v
Generated GLF Workbook + New-Allocation Workbook
   |
   | download .xlsx files
   v
User Browser
```

---

## 3. Recommended Repository Structure

```text
glf-assessment-scheduler/
  AGENTS.md
  PRD.md
  ARCHITECTURE.md
  TASKS.md
  README.md

  backend/
    requirements.txt
    pytest.ini
    app/
      __init__.py
      main.py
      api/
        __init__.py
        routes.py
      models/
        __init__.py
        allocation.py
        workbook.py
      services/
        __init__.py
        allocation_service.py
        excel_reader.py
        glf_parser.py
        roster_parser.py
        workbook_writer.py
      utils/
        __init__.py
        colours.py
        dates.py
        names.py
        errors.py
      tests/
        test_allocation_service.py
        test_colours.py
        test_dates.py
        test_glf_parser.py
        test_roster_parser.py
        test_workbook_writer.py

  frontend/
    package.json
    tsconfig.json
    vite.config.ts
    src/
      main.tsx
      App.tsx
      api/
        client.ts
      components/
        UploadForm.tsx
        ResultsSummary.tsx
        ResultsTable.tsx
        ErrorMessage.tsx
      types/
        allocation.ts
      styles/
        app.css
```

---

## 4. Backend Architecture

### 4.1 FastAPI App

Main responsibilities:

- Expose API endpoints.
- Validate uploaded files.
- Pass files to service layer.
- Return JSON results and downloadable workbook IDs.

Routes should stay thin. Do not put parsing or allocation logic in route handlers.

### 4.2 Backend API Endpoints

#### `GET /health`

Purpose:

- Simple health check.

Response:

```json
{
  "status": "ok"
}
```

#### `POST /api/generate-allocation`

Purpose:

- Accept uploaded workbooks and GLF password.
- Process allocation.
- Return summary, preview records, roster availability metadata, full GLF workbook download ID, and new-allocation workbook download ID.

Request:

```text
multipart/form-data
```

Fields:

| Field | Type | Required |
|---|---|---|
| `glf_workbook` | file | Yes |
| `roster_workbook` | file | Yes |
| `glf_password` | string | Yes |

Response:

```json
{
  "success": true,
  "summary": {
    "allocated": 0,
    "unallocated": 0,
    "skipped": 0
  },
  "records": [],
  "roster": {
    "allAssessors": [],
    "availableAssessorsByDate": {}
  },
  "download_id": "string",
  "preview_download_id": "string"
}
```

#### `GET /api/download/{download_id}`

Purpose:

- Download the generated `.xlsx` workbook.

Response:

- File download.
- Suggested filename: `GLF_Assessment_Generated_Allocation.xlsx`

#### `GET /api/download-preview/{download_id}`

Purpose:

- Download the separate new-allocation `.xlsx` workbook that follows the website preview table.

Response:

- File download.
- Suggested filename: `GLF_New_Allocation.xlsx`

---

## 5. Backend Modules

### 5.1 `excel_reader.py`

Responsibilities:

- Validate uploaded Excel files.
- Save uploaded files to temporary storage.
- Decrypt/read password-protected GLF workbook.
- Load workbooks with `openpyxl`.
- Return workbook objects to parser modules.

Important notes:

- Use the password entered by the user.
- Do not hardcode password in production flow.
- Return a clear error for wrong password.

---

### 5.2 `glf_parser.py`

Responsibilities:

- Read the second worksheet of the GLF Assessment Workbook.
- Identify assessee rows.
- Ignore section headers and legend rows.
- Find assessment columns:
  - Rx Check
  - Dispensing
  - Med Recon
  - MiniCeX
- Ignore:
  - CBD
  - PA
- Classify each assessment cell as:
  - Needs allocation
  - Already passed
  - Already allocated
  - Not applicable
  - Unsupported cell state
- Extract existing allocation history from Rx Check, Dispensing, Med Recon, and MiniCeX cells for repeat-assessor avoidance.

Expected output:

```python
list[GlfAssessmentNeed]
```

Each item should represent one assessee-assessment pair that is either allocatable, skipped, or already allocated.

---

### 5.3 `roster_parser.py`

Responsibilities:

- Read the first worksheet of the Roster Ward Allocation Workbook for OPS entries and non-ward GLF availability.
- Read the second worksheet of the Roster Ward Allocation Workbook for Ward allocation.
- Detect assessors with GLF availability.
- Classify yellow `GLF` cells as `Full day GLF` and yellow `/GLF` cells as `Half day GLF`.
- Detect assessee schedule date and location.
- Classify roster cell colours:
  - Yellow = GLF available assessor
  - Green = OPS
  - White cells in worksheet 2 = Ward
  - Non-white cells in worksheet 2 = ignored for Ward allocation
- Treat white Ward cells containing `{...}` as occupied/manual Ward cells that are fully ignored for automatic allocation. Names inside and outside braces in those cells do not create assessee entries or assessor availability. White Ward cells without `{...}` provide Ward assessor availability.
- Preserve the ward location label from column A for Ward preview output.
- Preserve the OPS shift label from green OPS cells in the first worksheet for OPS preview output.
- Collect all detected assessors with GLF or Ward availability and preserve availability grouped by date for frontend reporting.
- Return structured roster data.

Expected output:

```python
RosterData
```

This should include:

- Available assessors by date
- GLF availability type by assessor and date
- All detected available assessors
- Assessee locations by date
- Ward location labels for Ward assessees where available
- OPS shift labels for OPS assessees where available
- Assessee roster entries

---

### 5.4 `allocation_service.py`

Responsibilities:

- Match GLF assessment needs with roster availability.
- Enforce assessment location rules.
- Enforce assessor capacity rules.
- Run round-robin assessor selection.
- Avoid assessors already used for the same assessee in the GLF second worksheet for all allocatable assessment types, where possible.
- Allow new allocations created during the current generation to reuse the same assessor for the same assessee when capacity permits.
- Produce allocation records, including GLF section headers and display-ready locations such as `Ward (42A (1-8) RS-2)`.

This module is the core business logic layer.

---

### 5.5 `workbook_writer.py`

Responsibilities:

- Create the generated allocation worksheet.
- Insert it immediately after the first worksheet.
- Preserve existing worksheets.
- Preserve original workbook data, formatting, formulas, and colours as much as possible.
- Generate unique sheet names:
  - `Generated Allocation`
  - `Generated Allocation 2`
  - `Generated Allocation 3`
- Write allocation records into the new worksheet.
- Highlight successfully allocated copied assessment cells with a blue fill after writing assessor/date text.
- Save the updated workbook for download.
- Create a separate new-allocation workbook from allocated preview records.
- Use the preview columns `Date`, `Assessee`, `Header`, `Assessment`, `Location`, `Assessor`, `GLF Type`, `Status`, `Reason`, and `Cell`.
- Populate `GLF Type` with `Full day GLF` or `Half day GLF`.

---

### 5.6 Utility Modules

#### `colours.py`

Functions:

```python
is_black_fill(cell) -> bool
is_yellow_fill(cell) -> bool
is_green_fill(cell) -> bool
is_ward_fill(cell) -> bool
classify_location_from_fill(cell) -> LocationType
```

Colour detection should be tolerant because Excel may store colours as RGB, indexed colours, or theme colours.

#### `dates.py`

Functions:

```python
parse_date(value) -> date | None
format_date(value) -> str
```

Supported formats include:

- `10/3/26`
- `10/03/26`
- `22/4/26`
- `22/04/26`
- Excel date cells

Output format:

```text
DD/MM/YY
```

#### `names.py`

Functions:

```python
normalize_name(name: str) -> str
names_match(a: str, b: str) -> bool
```

Normalization rules:

1. Trim whitespace.
2. Collapse repeated spaces.
3. Compare case-insensitively.
4. Preserve original display names in outputs.

---

## 6. Frontend Architecture

### 6.1 Main Components

#### `UploadForm.tsx`

Responsibilities:

- Upload GLF workbook.
- Upload roster workbook.
- Accept GLF password.
- Validate required fields.
- Submit files to backend.

#### `ResultsSummary.tsx`

Responsibilities:

- Show allocated count.
- Show unallocated count.
- Show skipped count.

#### `ResultsTable.tsx`

Responsibilities:

- Display allocation preview rows.
- Show the GLF section header beside the assessee.
- Show Ward locations with the ward label in brackets when available.
- Show OPS locations with the OPS shift label in brackets when available.
- Show whether the assigned assessor was full-day or half-day GLF.
- Show status and reasons.
- Allow user to inspect unallocated records.
- Support filtering allocated preview rows by selected start and end dates.

#### Available/Unallocated Assessor Panel

Responsibilities:

- Use roster availability metadata returned by the backend.
- For the selected date range, show assessors who were rostered as GLF/available but were not assigned to any assessee in the filtered allocated records.
- Treat the panel as display-only; it does not change allocation output or downloadable workbooks.

#### `ErrorMessage.tsx`

Responsibilities:

- Display backend and frontend validation errors clearly.

### 6.2 API Client

`client.ts` should contain:

```ts
healthCheck(): Promise<HealthResponse>
generateAllocation(formData: FormData): Promise<GenerateAllocationResponse>
downloadWorkbook(downloadId: string): void
downloadPreviewWorkbook(downloadId: string): void
```

---

## 7. Data Models

### 7.1 Assessment Type

```python
AssessmentType = Literal["Rx Check", "Dispensing", "Med Recon", "MiniCeX"]
```

### 7.2 Location Type

```python
LocationType = Literal["Ward", "OPS", "Unknown"]
```

### 7.3 Allocation Status

```python
AllocationStatus = Literal[
    "Allocated",
    "Unallocated",
    "Skipped - Already Passed",
    "Skipped - Already Allocated",
    "Skipped - Not Applicable",
    "Skipped - Unsupported Cell State",
]
```

### 7.4 Allocation Record

```python
@dataclass
class AllocationRecord:
    date: str
    assessee_name: str
    glf_section_header: str
    assessment_type: str
    assessee_location: str
    assigned_assessor: str
    assessor_glf_availability_date: str
    status: str
    reason: str
    original_glf_cell_reference: str
    existing_allocation_history: str
```

---

## 8. Core Allocation Logic

For each assessment need from the GLF workbook:

1. Skip if black-filled.
2. Skip if cell already contains text.
3. Skip if assessment is CBD or PA.
4. Match assessee to roster.
5. Determine date and location.
6. Determine valid location for assessment:
   - Rx Check = Ward or OPS
   - Dispensing = OPS only
   - Med Recon = Ward only
   - MiniCeX = Ward only
7. Find available assessors with GLF availability on same date. For Ward allocation, ignore brace-containing Ward cells entirely before matching assessees or assessors.
8. Filter assessors by location compatibility.
9. Filter assessors by capacity:
   - Total assessments < 4
   - MiniCeX assessments < 2 if MiniCeX
10. For Rx Check, Dispensing, Med Recon, and MiniCeX, avoid existing assessor history for that assessee from the GLF second worksheet.
    New allocations made in the current generation are controlled by capacity rules and may reuse the same assessor for the same assessee.
11. Use round-robin tie-breaking.
12. Create allocation record.
13. If no assessor is available, create unallocated record with reason.

---

## 9. Preview Output Structure

The API preview records and the separate new-allocation workbook use these fields:

| Column | Field |
|---|---|
| A | Date |
| B | Assessee Name |
| C | Assessment Type |
| D | Assessee Location |
| E | Assigned Assessor |
| F | Assessor GLF Availability Date |
| G | Status |
| H | Reason if Unallocated or Skipped |
| I | Original GLF Cell Reference |
| J | Existing Allocation History |

The website preview table should show a display-oriented subset of the allocation record fields:

| Column | Field |
|---|---|
| Date | Date |
| Assessee | Assessee Name |
| Header | GLF Section Header |
| Assessment | Assessment Type |
| Location | Assessee Location |
| Assessor | Assigned Assessor |
| GLF Type | Assessor GLF Availability Type |
| Status | Status |
| Reason | Reason or Existing Allocation History |
| Cell | Original GLF Cell Reference |

For Ward allocations, `Assessee Location` should include the ward label in brackets when it is available from the roster second worksheet row heading, for example `Ward (42A (1-8) RS-2)`.

For OPS allocations, `Assessee Location` should include the OPS shift label in brackets when it is available from the green OPS roster cell, for example `OPS (A)`, `OPS (C)`, `OPS (D)`, `OPS (ICT)`, or `OPS (C1)`. If no shift label is available, display `OPS`.

The separate new-allocation workbook should contain the same display-oriented preview columns and only successfully allocated rows. It is a separate `.xlsx` artifact and does not replace the full updated GLF workbook.

The frontend results view should also provide start-date and end-date controls. These controls filter the displayed allocated preview rows only; they do not alter backend allocation records or generated workbooks. Date options should come from allocation record dates and roster availability dates.

The same selected date range should drive an informational list of assessors who were rostered as GLF/available in that range but were not assigned any assessee in the filtered allocated preview records. The calculation is:

```text
available assessors by date in selected range
minus
assigned assessors in filtered allocated records
```

---

## 10. Security and Privacy Notes

- Uploaded files may contain personal data.
- Do not store uploaded files permanently.
- Use temporary storage only.
- Do not log full workbook content.
- Do not log passwords.
- Do not expose stack traces to frontend users.
- Return clear but safe error messages.

---

## 11. Testing Architecture

Test the logic in layers:

1. Utility tests
   - Colour detection
   - Date parsing
   - Name normalization
2. Parser tests
   - GLF workbook parser
   - Roster workbook parser
   - Brace-containing Ward cells do not create automatic assessee entries or assessor availability
3. Allocation tests
   - Capacity limits
   - Location compatibility
   - Round-robin logic
   - Repeat-assessor avoidance
4. Writer tests
   - Generated worksheet insertion
   - Sheet-name incrementing
   - Workbook preservation
   - Separate new-allocation workbook columns and allocated-only rows
5. API tests
   - File validation
   - Wrong password handling
   - Successful allocation response
   - Roster availability metadata in successful allocation response
6. Frontend tests or manual verification
   - Date range filtering of allocated preview rows
   - Available-but-not-allocated assessor list for selected date range
