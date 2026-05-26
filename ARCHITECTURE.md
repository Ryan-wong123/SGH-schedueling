# ARCHITECTURE.md

## 1. System Overview

The GLF Assessment Scheduler is a web application that processes two Excel files and generates a new allocation worksheet inside the GLF Assessment Workbook.

The system has two main parts:

1. **Frontend** — React TypeScript application for uploading files, entering the password, previewing results, and downloading the generated workbook.
2. **Backend** — FastAPI application for reading Excel files, parsing workbook data, running allocation logic, and returning the generated workbook.

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
Generated GLF Workbook
   |
   | download .xlsx
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
- Return JSON results and downloadable workbook.

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
- Return summary, preview records, and download ID.

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
  "download_id": "string"
}
```

#### `GET /api/download/{download_id}`

Purpose:

- Download the generated `.xlsx` workbook.

Response:

- File download.
- Suggested filename: `GLF_Assessment_Generated_Allocation.xlsx`

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
- Extract existing allocation history for repeat-assessor avoidance.

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
- Detect assessee schedule date and location.
- Classify roster cell colours:
  - Yellow = GLF available assessor
  - Green = OPS
  - White cells in worksheet 2 = Ward
  - Non-white cells in worksheet 2 = ignored for Ward allocation
- Preserve the ward location label from column A for Ward preview output.
- Return structured roster data.

Expected output:

```python
RosterData
```

This should include:

- Available assessors by date
- Assessee locations by date
- Ward location labels for Ward assessees where available
- Assessee roster entries

---

### 5.4 `allocation_service.py`

Responsibilities:

- Match GLF assessment needs with roster availability.
- Enforce assessment location rules.
- Enforce assessor capacity rules.
- Run round-robin assessor selection.
- Avoid repeated assessors for MiniCeX and Med Recon where possible.
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
- Save the updated workbook for download.

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
- Show status and reasons.
- Allow user to inspect unallocated records.

#### `ErrorMessage.tsx`

Responsibilities:

- Display backend and frontend validation errors clearly.

### 6.2 API Client

`client.ts` should contain:

```ts
healthCheck(): Promise<HealthResponse>
generateAllocation(formData: FormData): Promise<GenerateAllocationResponse>
downloadWorkbook(downloadId: string): void
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
7. Find available assessors with GLF availability on same date.
8. Filter assessors by location compatibility.
9. Filter assessors by capacity:
   - Total assessments < 4
   - MiniCeX assessments < 2 if MiniCeX
10. For MiniCeX and Med Recon, avoid existing assessor history for that assessee.
11. Use round-robin tie-breaking.
12. Create allocation record.
13. If no assessor is available, create unallocated record with reason.

---

## 9. Generated Worksheet Structure

The generated worksheet must contain these columns:

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
| Status | Status |
| Reason | Reason or Existing Allocation History |
| Cell | Original GLF Cell Reference |

For Ward allocations, `Assessee Location` should include the ward label in brackets when it is available from the roster second worksheet row heading, for example `Ward (42A (1-8) RS-2)`. OPS allocations should display as `OPS`.

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
3. Allocation tests
   - Capacity limits
   - Location compatibility
   - Round-robin logic
   - Repeat-assessor avoidance
4. Writer tests
   - Generated worksheet insertion
   - Sheet-name incrementing
   - Workbook preservation
5. API tests
   - File validation
   - Wrong password handling
   - Successful allocation response
