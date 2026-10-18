# Project: GLF Assessment Scheduler Website

## 1. Project Goal

Build a web application that performs scheduling allocation of assessors to assessees for GLF assessments.

The website must accept two Excel workbook inputs:

1. GLF Assessment Workbook
2. Roster Ward Allocation Workbook

The GLF Assessment Workbook is password protected. The website must provide a password input field so the user can enter the password before the backend reads the workbook.

For testing, the GLF workbook password is:

```text
coreassessor
```

The website should allocate assessors to assessees for the following assessment types:

- Rx Check
- Dispensing
- Med Recon
- MiniCeX

These assessment types are columns inside the GLF Assessment Workbook.

The system must generate an updated GLF Assessment Workbook as output. The output workbook must preserve all existing worksheets, data, formulas, formatting, and colours as much as possible.

The system must also generate a separate new-allocation workbook for download. This second workbook is in addition to the full updated GLF workbook and should follow the same columns and rows shown in the website allocation preview.

---

## 2. Recommended Tech Stack

Use the following stack unless there is a strong reason not to:

### Backend

- Python
- FastAPI
- openpyxl for reading/writing Excel formatting and cell colours
- msoffcrypto-tool or equivalent library for reading password-protected Excel files
- tempfile for temporary file handling

### Frontend

- React
- TypeScript
- Simple upload form UI
- Results preview table
- Download buttons for the full updated GLF workbook and the separate new-allocation workbook

### General Requirements

- Do not store uploaded files permanently.
- Process files in temporary storage only.
- Delete temporary files after processing when possible.
- Do not hardcode the workbook password in production logic.
- Use the password entered by the user to decrypt/read the uploaded GLF workbook.
- Return clear validation errors to the user.

---

## 3. Website User Flow

The website should have a simple workflow:

1. User uploads the GLF Assessment Workbook.
2. User uploads the Roster Ward Allocation Workbook.
3. User enters the GLF workbook password.
4. User clicks `Generate Allocation`.
5. Backend validates and processes both workbooks.
6. Website displays:
   - Allocation summary
   - Allocated records
   - Skipped records
   - Unallocated records with reasons
   - Date range controls for filtering allocated preview records
   - Assessors who were rostered as GLF/available in the selected date range but were not allocated any assessee
7. User can download the updated GLF workbook.
8. User can download a separate new-allocation workbook that matches the website preview output.

---

## 4. Input File 1: Roster Ward Allocation Workbook

### 4.1 Workbook Rule

Use the first worksheet of the Roster Ward Allocation Workbook for everything: OPS entries, non-ward GLF availability, and Ward allocation. Other worksheets in the roster workbook are not read.

Each row of the first worksheet is a person (name in column A), and each date column holds that person's location for the day.

### 4.2 GLF Availability Rule

In the first worksheet of the roster workbook:

- Rows with the `GLF` cell highlighted yellow are assessors who are free for the whole day.
- Rows with the `/GLF` or `GLF/` cell highlighted yellow are assessors who are free for a half day.
- These assessors are eligible to perform non-ward assessments for assessees on that GLF availability date.

The system must identify assessors with GLF availability by reading the cell fill colour.

For Ward allocation, the system must use the white cells of the first worksheet:

- Only white-filled cells are used.
- Braces `{...}` are ignored: the `{` and `}` characters are removed and the text inside is classified as ward or non-ward like any other value (e.g. `{45A}` is used as `Ward ({45A})`, `67A / {CICU}` is used as `Ward (67A {CICU})`, `{CICU}` alone is excluded). The braces are removed only for this check; the Ward label keeps them.
- White cells must contain a ward value to be used. A ward value is a two-digit ward number, usually followed by a letter, suffix or bracketed bed range (e.g. `11B`, `45A`, `58 ISO`, `63(12-14)`, `68ICU`), found anywhere in the cell text regardless of separators. Cells with only non-ward values (e.g. `Admin`, `MICU`, `CTS`, `DI`, `IPAS/IDD`, `SGH@Home Command Centre`, `WR - IM`, `Clinic-1`, `NICU-1 / NICU-2 / CCU`) are ignored. Cells mixing ward and non-ward values (e.g. `45A / MICA`) are used.
- A used white cell creates a Ward availability and a Ward date/location entry for the person in column A of that row. Only people listed in column A of the second GLF workbook worksheet are assessment candidates; a roster name matching any of those GLF assessees is never eligible as an assessor.
- The ward location label is the white cell's own text and should be preserved for preview output.
- OPS shift labels are taken from green OPS cells in the first worksheet and should be preserved for preview output.
- `floater` / `*floater*` text is a roster placeholder and must not be treated as an assessor or assessee.

### 4.3 Location Colour Rule

Inside the roster worksheet, colour-coded cells represent different assessment locations.

The system must read the Excel cell fill colour to determine location.

Use the following location rules:

| Colour / Cell Type | Meaning |
|---|---|
| Green cells in worksheet 1 | OPS |
| White cells in worksheet 1 with a ward value | Ward |
| Other cells in worksheet 1 | Ignore for Ward allocation |

### 4.4 Assessment Location Compatibility

Each assessment type has a location requirement.

| Assessment Type | Required Location |
|---|---|
| MiniCeX | Ward only |
| Med Recon | Ward only |
| Dispensing | OPS only |
| Rx Check | Ward or OPS |

Rules:

- MiniCeX assessees must be scheduled at ward locations.
- Med Recon assessees must be scheduled at ward locations.
- Dispensing assessees must be scheduled at OPS locations.
- Rx Check assessees can be scheduled at either ward or OPS.

### 4.5 Matching Rule

The system must pair assessors with GLF availability to assessees based on:

1. Same relevant date
2. Correct assessee location
3. Assessment type compatibility
4. Assessor daily capacity
5. Assessor is not any person listed in column A of the GLF progress worksheet
6. Assessor and assessee must be different people
7. Round-robin balancing

---

## 5. Input File 2: GLF Assessment Workbook

### 5.1 Password Protection

The GLF Assessment Workbook is password protected.

The user must enter the password in the website.

For testing, the password is:

```text
coreassessor
```

The backend must use the provided password to read the workbook.

If the password is wrong, return a clear error message:

```text
Unable to open GLF Assessment Workbook. Please check the password and try again.
```

### 5.2 Important Worksheet Rule

Always refer to the second worksheet of the GLF Assessment Workbook as the current assessment progress worksheet.

The second worksheet contains:

- Assessees
- Their assessment progress
- Existing assessor allocations
- Cells showing which assessments are already passed
- Cells showing which assessments still require allocation

Do not overwrite the original second worksheet.

### 5.3 Expected GLF Worksheet Structure

The second worksheet generally has the following column layout:

| Column | Meaning |
|---|---|
| A | Assessee name / section header |
| B | Mentor |
| C | Appraiser |
| D | Preceptor |
| E | MM/YY joined |
| F | MM/YY first registered |
| G | Rx Check |
| H | Dispensing |
| I | Med Recon |
| J | MiniCeX |
| K | CBD |
| L | PA |

Only these assessment columns are used for scheduling allocation:

- Rx Check
- Dispensing
- Med Recon
- MiniCeX

Ignore these columns for allocation:

- CBD
- PA

Even if CBD and PA contain data, they must not be part of the automatic scheduling logic.

### 5.4 Assessee Detection

A row should be treated as an assessee row only if:

1. Column A contains a person’s name.
2. The row is not a section header.
3. The row is not a legend row.
4. The person exists in the GLF assessment progress worksheet.
5. The person can be matched with a corresponding person in the roster workbook.

Rows such as the following are section headers and must not be allocated:

- Y2
- Y1
- New Pre-reg > OPRs
- Legend

For each assessee row, preserve the most recent GLF section header above that row, such as `Y10`, `Y7`, `Y1`, or `New Pre-reg > OPRs`, so it can be shown in the website preview table.

If a person exists in the roster workbook but does not exist in the GLF Assessment Workbook, do not allocate any assessment for that person.

### 5.5 Assessment Cell Meaning

For every assessee row, check only these GLF assessment columns:

| Column | Assessment |
|---|---|
| G | Rx Check |
| H | Dispensing |
| I | Med Recon |
| J | MiniCeX |

Each cell must be interpreted as follows.

---

### 5.5.1 Blank Cell

A blank cell means the assessee still needs that assessment to be allocated.

The system should attempt to assign an eligible assessor.

Example:

If the Med Recon cell is blank for an assessee, the system should try to assign a valid assessor for Med Recon.

---

### 5.5.2 Cell With Existing Text

If the cell already contains text, it means the assessment has already been allocated or completed.

Examples of existing text:

```text
Ama 10/3/26
Mel 22/4/26
Cheryl 08/04/26
Sher Ri 24/3/26
```

Rules:

- Do not overwrite cells with existing text.
- Treat the text as existing allocation history.
- Record it in the generated output worksheet as skipped or existing history.

For all allocatable assessment types:

- Avoid assigning the same assessor already used for that assessee from the GLF second worksheet, where possible.
- The system should read existing Rx Check, Dispensing, Med Recon, and MiniCeX cells for that assessee and avoid repeating those existing assessors if possible.
- New allocations created during the current generation do not count as existing history for this rule. If the assigned assessor still has capacity for that date, they may be allocated to another assessment for the same assessee.

---

### 5.5.3 Black-Filled Cell

If a cell is black-filled, it means the assessee has passed out of that assessment for this cycle.

Rules:

- Do not allocate an assessor.
- Do not overwrite the cell.
- Mark it as:

```text
Skipped - Already Passed
```

in the generated allocation output.

---

### 5.5.4 Non-Blank Coloured Cells

Some cells may contain colours such as purple or yellow to indicate notes, transfer information, rotation information, or special states.

Rules:

- Do not overwrite coloured cells unless they are clearly blank assessment cells requiring allocation.
- If a coloured cell has text, treat it as existing information and skip it.
- If a coloured cell is not clearly allocatable, mark it as skipped with an explanatory reason.

---

## 6. Assessment Capacity Rules

Each assessor can be assigned at most 4 assessments per full GLF day (`GLF`), or 2 per half GLF day (`/GLF` or `GLF/`). Ward availability defaults to the full-day limit.

Each assessor can only be assigned a maximum of 2 MiniCeX assessments per day.

Use these rules programmatically:

```text
Full day: Rx Check + Dispensing + Med Recon + MiniCeX <= 4
Half day: Rx Check + Dispensing + Med Recon + MiniCeX <= 2
An assessor cannot mix MiniCeX/Med Recon with Rx Check/Dispensing on the same date.
MiniCeX <= 2
```

Do not hardcode the 31 scenario table as the allocation logic.

The scenario table is only a reference showing valid combinations.

Examples of valid daily combinations include:

| Rx Check | Dispensing | Med Recon | MiniCeX |
|---:|---:|---:|---:|
| 4 | 0 | 0 | 0 |
| 0 | 4 | 0 | 0 |
| 0 | 0 | 4 | 0 |
| 2 | 2 | 0 | 0 |
| 0 | 0 | 2 | 2 |

These examples assume full-day availability; half-day totals must not exceed 2.

Invalid examples:

| Rx Check | Dispensing | Med Recon | MiniCeX | Reason |
|---:|---:|---:|---:|---|
| 2 | 1 | 1 | 1 | Total is 5 assessments |
| 0 | 0 | 1 | 3 | MiniCeX exceeds 2 |
| 1 | 0 | 1 | 0 | Assessment groups mixed |

---

## 7. Round-Robin Allocation Rule

Use round-robin allocation among eligible assessors so that the same assessor is not always scheduled for every assessment.

For each assessment date:

1. Maintain a rotating list of available assessors.
2. Filter assessors by GLF availability.
3. Filter assessors by location compatibility.
4. Filter assessors by daily capacity and exclude assessors already assigned to the other assessment group on that date.
5. Exclude every person listed in column A of the GLF progress worksheet from the assessor candidate list, including shortened roster-name variants.
6. After existing-history avoidance, prefer an assessor already assigned to the same assessee on that date, then an assessor already working in the same assessment group. Among equally preferred assessors, choose the lowest assignment count for that date.
7. If tied, assign the assessor who was least recently used.
8. If still tied, sort by assessor name alphabetically.

### 7.1 Capacity Check During Round-Robin

Before assigning an assessor, check:

```text
assessor_total_assignments_for_date < (2 for Half day GLF, otherwise 4)
assessor has no assignments from the other assessment group on that date
```

For MiniCeX, also check:

```text
assessor_minicex_assignments_for_date < 2
```

### 7.2 Repeat Assessor Avoidance

For Rx Check, Dispensing, Med Recon, and MiniCeX:

- Avoid assigning the same assessor already used for that assessee in the GLF second worksheet, where possible.
- Existing assessor history must be read from that assessee's Rx Check, Dispensing, Med Recon, and MiniCeX cells.
- Do not treat new allocations made during the current generation as repeat history. For the same assessee on the same date, prefer reusing the assessor already selected during the current generation when that assessor is eligible for the assessment location and still has capacity under the daily capacity rules.
- If all eligible assessors were already used in the GLF second worksheet, apply grouping, daily load, least-recent-use and alphabetical tie-breakers to those candidates and mark the reason as:

```text
Repeated assessor used because no alternative eligible assessor was available.
```

---

## 8. Allocation Algorithm

Implement the allocation logic using the following high-level algorithm.

### Step 1: Read Inputs

1. Receive uploaded GLF workbook.
2. Receive uploaded roster workbook.
3. Receive GLF workbook password.
4. Decrypt/read GLF workbook using password.
5. Read roster workbook normally.
6. Validate that both workbooks have the expected worksheets.

### Step 2: Parse GLF Progress

1. Open the second worksheet of the GLF workbook.
2. Identify assessee rows.
3. Read assessment columns:
   - Rx Check
   - Dispensing
   - Med Recon
   - MiniCeX
4. For each assessee and each assessment:
   - Blank cell = needs allocation.
   - Black-filled cell = skip as already passed.
   - Cell with text = skip as already allocated.
   - Unsupported coloured cell = skip unless clearly blank and allocatable.
   - Preserve the current GLF section header for preview output.

### Step 3: Parse Roster

1. Open the first worksheet of the roster workbook for OPS entries and non-ward GLF availability.
2. Use the same first worksheet of the roster workbook for Ward allocation.
3. Detect non-ward assessors with yellow GLF availability in worksheet 1.
4. Detect OPS assessee date and location from green cells in worksheet 1.
5. Detect Ward assessors from white worksheet 1 cells that contain a ward value (after removing `{` and `}`), and create Ward date/location entries for the person in column A of that row.
6. Remove `{` and `}` characters and classify the inner text normally; keep the braces in the Ward label.
7. Capture the ward location label from the white Ward cell's own text.
8. Ignore white worksheet 1 cells with no ward value, and non-white cells, for Ward allocation.
9. Classify locations:
   - Green cells in worksheet 1 = OPS
   - White cells in worksheet 1 with a ward value = Ward

### Step 4: Match Assessees

For each assessee requiring allocation:

1. Confirm the assessee exists in the GLF workbook.
2. Find the corresponding assessee in the roster workbook.
3. Determine the required assessment type.
4. Determine the assessee’s date and location.
5. Filter available assessors by:
   - Same date
   - GLF availability
   - Location compatibility
   - Capacity
   - Existing GLF history repeat-assessor rule
6. Use round-robin to pick the best assessor.
7. If an assessor is found, create an allocated record.
8. If no assessor is found, create an unallocated record with a reason.

### Step 5: Generate Output Worksheet

1. Create a new worksheet in the GLF workbook.
2. Insert it immediately after the first worksheet.
3. Name it:

```text
Generated Allocation
```

4. If that name already exists, use:

```text
Generated Allocation 2
Generated Allocation 3
Generated Allocation 4
```

and so on.

5. Copy the current GLF progress worksheet as the generated worksheet.
6. Write only successful allocated assessor/date values into the copied assessment cells.
7. Do not write skipped or unallocated records into assessment cells.
8. Clear copied values from black-filled passed cells in the generated worksheet while preserving the black fill.
9. Preserve all existing worksheets.
10. Do not delete or overwrite the original second worksheet.
11. Return the full updated GLF workbook for download.
12. Also return a separate new-allocation workbook for download using the website preview output fields.

---

## 9. Output Workbook Requirements

The website should update the GLF Assessment Workbook by adding a new worksheet.

The new worksheet must be placed immediately after the first worksheet.

The output file must include:

- Original first worksheet
- New Generated Allocation worksheet
- Original second worksheet
- All other original worksheets

The system must not remove any worksheets.

The system must not overwrite the original second worksheet.

The output workbook should preserve as much of the original workbook as possible, including:

- Existing data
- Existing formulas
- Existing formatting
- Existing colours
- Existing worksheets

---

## 10. Generated Allocation Worksheet Format

The generated worksheet should be a copy of the original GLF progress worksheet.

The system should write allocation results directly into the copied assessment cells:

- For `Allocated` records, write `Assessor Date` into the original GLF cell reference on the copied worksheet.
- Highlight copied cells written for `Allocated` records with a blue fill.
- For `Skipped - Already Passed` records, leave the copied cell black-filled and clear any copied text value.
- For `Skipped - Already Allocated` records, preserve the existing copied assessor/date text.
- For `Unallocated` records, leave the copied cell blank.
- Do not modify the original GLF progress worksheet.

The backend API response should still return allocation records for preview in the frontend, including:

- Date
- Assessee Name
- GLF Section Header
- Assessment Type
- Assessee Location
- Assigned Assessor
- Assessor GLF Availability Date
- Assessor GLF Availability Type
- Status
- Reason if Unallocated or Skipped
- Original GLF Cell Reference
- Existing Allocation History

For website preview output, the `Assessee Location` value must include the ward label in brackets for Ward allocations when available, for example `Ward (42A (1-8) RS-2)`. OPS allocations should continue to display as `OPS`.

OPS locations display as `OPS`, following AGENTS.md. Shift labels may be retained internally but are not included in the preview or new-allocation workbook.

The API response should also return roster availability metadata for the generated result, including:

- All detected assessors with GLF or Ward availability.
- Available assessors grouped by roster date.

The frontend uses this metadata only for display and filtering after generation; it must not alter the allocation records or generated workbooks.

### 10.1 New-Allocation Workbook Format

In addition to the full updated GLF workbook, the backend must create a separate workbook for the newly generated allocation preview.

This workbook must:

- Be a standalone `.xlsx` file.
- Contain a worksheet named `New Allocation`.
- Include only successfully allocated records.
- Use the same display columns as the website preview table:
  - Date
  - Assessee
  - Header
  - Assessment
  - Location
  - Assessor
  - Status
  - Reason
  - Cell
- Preserve display-ready Ward locations such as `Ward (42A (1-8) RS-2)`.
- Display OPS locations as `OPS`.
- Be downloaded separately from the full updated GLF workbook.

### 10.2 Status Values

Use only these status values:

| Status | Meaning |
|---|---|
| Allocated | A valid assessor was assigned |
| Unallocated | No valid assessor could be found |
| Skipped - Already Passed | The assessment cell is black-filled |
| Skipped - Already Allocated | The assessment cell already contains assessor/date text |
| Skipped - Not Applicable | The row or cell should not be automatically scheduled |
| Skipped - Unsupported Cell State | The cell colour or state is unclear |

### 10.3 Example API Preview Rows

| Date | Assessee Name | GLF Section Header | Assessment Type | Assessee Location | Assigned Assessor | Assessor GLF Availability Date | Assessor GLF Availability Type | Status | Reason if Unallocated or Skipped | Original GLF Cell Reference | Existing Allocation History |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10/03/26 | Amanda Chua Jing Yi | Y1 | Rx Check | Ward (42A (1-8) RS-2) | Cheryl | 10/03/26 | Full day GLF | Allocated |  | G45 |  |
| 15/04/26 | Celine Sia Si Lin | Y2 | Med Recon | Ward (45A) | Gen | 15/04/26 | Half day GLF | Allocated |  | I46 |  |
| 08/04/26 | Chan Xiao Ting, Kristy | Y3 | MiniCeX | Ward |  |  |  | Skipped - Already Allocated | Existing allocation found | J47 | Cheryl 08/04/26 |
| 22/04/26 | Megan Goh | Y3 | Dispensing | OPS |  |  |  | Unallocated | No available assessor with OPS-compatible availability | H23 |  |
|  | Denise Song | Y4 | Rx Check |  |  |  |  | Skipped - Already Passed | Black-filled cell | G23 |  |

---

## 11. Frontend Requirements

Create a simple frontend with the following sections.

### 11.1 Upload Form

Fields:

- GLF Assessment Workbook upload
- Roster Ward Allocation Workbook upload
- GLF Workbook Password input
- Generate Allocation button

Validation:

- Both files must be uploaded.
- Password must not be empty.
- Files must be Excel files with `.xlsx` extension.

### 11.2 Processing State

Show a loading indicator while files are being processed.

Example:

```text
Generating allocation, please wait...
```

### 11.3 Results View

After processing, show:

1. Total allocated count
2. Total unallocated count
3. Total skipped count
4. Preview table of generated records
5. Download updated GLF workbook button
6. Download new-allocation workbook button
7. Start date and end date controls for filtering allocated preview records by allocation date
8. A list of assessors who were rostered as GLF/available during the selected date range but were not assigned any assessee in the filtered allocation records
9. The preview columns are exactly Date, Assessee, Header, Assessment, Location, Assessor, Status, Reason, Cell, following AGENTS.md. Availability type remains API metadata.

### 11.4 Date Range Filter

The results view must let the user choose a start date and end date from dates detected in the generated allocation records and roster availability metadata.

Rules:

- If no start date is selected, use the earliest available date.
- If no end date is selected, use the latest available date.
- If the user selects the dates in reverse order, treat the earlier selected date as the start and the later selected date as the end.
- Filter the website allocation preview table to allocated records whose allocation date is inside the selected range.
- The date range filter is a website preview feature only. It must not change the generated GLF workbook or the separate new-allocation workbook.

### 11.5 Available But Not Allocated Assessors

For the selected date range, the results view must show assessors who:

1. Were detected as GLF/available assessors in the roster workbook for at least one date in the selected range.
2. Were not assigned to any assessee in the filtered allocation records for that same selected range.

This list is calculated as:

```text
rostered/available assessors in selected date range
minus
assessors assigned at least one assessee in selected date range
```

This list is informational only. It must not create, remove, or change allocations.

### 11.6 Error Display

Show clear error messages for:

- Wrong GLF workbook password
- Missing workbook
- Invalid file type
- Missing expected worksheet
- Missing expected columns
- Unable to detect GLF availability
- Unable to detect assessee location
- No valid assessor found
- Unexpected processing error

---

## 12. Backend API Requirements

Create these API endpoints.

### 12.1 Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### 12.2 Generate Allocation

```http
POST /api/generate-allocation
```

Request type:

```text
multipart/form-data
```

Fields:

| Field | Type | Required |
|---|---|---|
| glf_workbook | file | Yes |
| roster_workbook | file | Yes |
| glf_password | string | Yes |

Response:

If successful, return JSON containing:

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

### 12.3 Download Output Workbook

```http
GET /api/download/{download_id}
```

Response:

- Return the generated `.xlsx` file.
- Use a clear filename such as:

```text
GLF_Assessment_Generated_Allocation.xlsx
```

### 12.4 Download New-Allocation Workbook

```http
GET /api/download-preview/{preview_download_id}
```

Response:

- Return the separate new-allocation `.xlsx` file.
- Use a clear filename such as:

```text
GLF_New_Allocation.xlsx
```

---

## 13. Suggested Backend Structure

Use a clean modular backend structure.

```text
backend/
  app/
    main.py
    api/
      routes.py
    services/
      allocation_service.py
      excel_reader.py
      glf_parser.py
      roster_parser.py
      workbook_writer.py
    models/
      allocation.py
      workbook.py
    utils/
      colours.py
      dates.py
      names.py
    tests/
      test_glf_parser.py
      test_roster_parser.py
      test_allocation_rules.py
      test_workbook_writer.py
  requirements.txt
```

---

## 14. Suggested Frontend Structure

Use a clean React frontend structure.

```text
frontend/
  src/
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
```

---

## 15. Data Models

Use internal data models similar to the following.

### 15.1 Assessment Type

```ts
type AssessmentType = "Rx Check" | "Dispensing" | "Med Recon" | "MiniCeX";
```

### 15.2 Location Type

```ts
type LocationType = "Ward" | "OPS" | "Unknown";
```

### 15.3 Allocation Status

```ts
type AllocationStatus =
  | "Allocated"
  | "Unallocated"
  | "Skipped - Already Passed"
  | "Skipped - Already Allocated"
  | "Skipped - Not Applicable"
  | "Skipped - Unsupported Cell State";
```

### 15.4 Allocation Record

```ts
interface AllocationRecord {
  date: string;
  assesseeName: string;
  glfSectionHeader: string;
  assessmentType: AssessmentType;
  assesseeLocation: string;
  assignedAssessor: string;
  assessorGlfAvailabilityDate: string;
  assessorGlfAvailabilityType: string;
  status: AllocationStatus;
  reason: string;
  originalGlfCellReference: string;
  existingAllocationHistory: string;
}
```

---

## 16. Colour Detection Requirements

The system must inspect Excel cell fill colours.

Create helper functions to classify colours.

### 16.1 GLF Workbook Colours

In the GLF Assessment Workbook:

| Colour | Meaning |
|---|---|
| Black | Passed out / skip allocation |
| Blank or no fill | Potentially needs allocation if cell is empty |
| Other colour with text | Existing note or information / skip |
| Other colour without text | Unsupported unless explicitly mapped |

### 16.2 Roster Workbook Colours

In the Roster Ward Allocation Workbook:

| Colour | Meaning |
|---|---|
| Yellow in GLF cell on worksheet 1 | Assessor available for non-ward allocation |
| Green on worksheet 1 | OPS location |
| White on worksheet 1 with a ward value | Ward location for assessors and assessees |
| Other cells on worksheet 1 | Ignore for Ward allocation |

Because Excel colours may appear as RGB, indexed colours, or theme colours, implement colour detection in a tolerant way.

Do not rely on exact RGB only. Build helper functions such as:

```python
is_yellow_fill(cell) -> bool
is_black_fill(cell) -> bool
is_green_fill(cell) -> bool
is_ward_fill(cell) -> bool
classify_location_from_fill(cell) -> "Ward" | "OPS" | "Unknown"
```

---

## 17. Name Matching Requirements

Names may have different spacing or capitalization between workbooks.

Implement basic normalization:

1. Trim leading/trailing spaces.
2. Collapse multiple spaces into one.
3. Compare case-insensitively.
4. Preserve the original display name in output.

Example:

```text
"Chan Xiao Ting, Kristy"
"chan xiao ting, kristy"
```

should be treated as the same name.

Do not use fuzzy matching unless implemented carefully.

If no exact normalized match is found, mark the record as unallocated with reason:

```text
Assessee not found in roster workbook.
```

---

## 18. Date Handling Requirements

Dates may appear in different formats.

Handle common Excel and text date formats, such as:

```text
10/3/26
10/03/26
22/4/26
22/04/26
```

The generated worksheet should display dates consistently as:

```text
DD/MM/YY
```

If a date cannot be parsed, preserve the original value and add a warning reason.

---

## 19. Validation Rules

Before allocation, validate:

1. GLF workbook can be opened with the provided password.
2. GLF workbook has at least 2 worksheets.
3. Roster workbook has at least 1 worksheet.
4. GLF second worksheet contains expected assessment columns:
   - Rx Check
   - Dispensing
   - Med Recon
   - MiniCeX
5. Roster workbook contains enough data to identify:
   - Assessors
   - Assessees
   - GLF availability
   - Dates
   - Locations

If validation fails, return a clear error and do not generate a workbook.

---

## 20. Error Handling

Return user-friendly errors.

Examples:

```text
Wrong GLF workbook password.
```

```text
The GLF workbook must contain at least two worksheets.
```

```text
The roster workbook must contain at least one worksheet.
```

```text
Could not find required assessment column: MiniCeX.
```

```text
No eligible assessor found for this assessee, assessment, date, and location.
```

```text
Assessor has reached maximum daily capacity.
```

---

## 21. Testing Requirements

Create automated tests for the core logic.

At minimum, test:

1. GLF workbook password handling.
2. Roster workbook uses the first worksheet for OPS/non-ward availability and for Ward allocation from white cells that contain a ward value (braces removed before checking).
3. White Ward cells with no ward value (braces removed before checking) are fully ignored and do not create automatic assessee entries or assessor availability.
4. GLF workbook uses the second worksheet as progress source.
5. Black-filled GLF cells are skipped.
6. Blank GLF assessment cells are considered for allocation.
7. Existing text cells are skipped.
8. CBD and PA columns are ignored.
9. Rx Check, Dispensing, Med Recon, and MiniCeX avoid assessors already used for the same assessee in the GLF second worksheet, where possible.
10. Full-day limit 4, half-day limit 2, MiniCeX limit 2, and same-day group separation are enforced.
11. Assessor max 2 MiniCeX per day is enforced.
12. Dispensing only matches OPS.
13. MiniCeX only matches Ward.
14. Med Recon only matches Ward.
15. Rx Check matches Ward or OPS.
16. Round-robin chooses the least-assigned eligible assessor.
17. An assessee is never assigned to assess themself, including where the roster uses a shortened form of the same name.
18. A person listed in column A of the GLF progress worksheet is never selected as an assessor for another person.
19. New worksheet is inserted after the first worksheet.
20. Existing second worksheet is preserved and shifted.
21. Existing worksheets, formulas, formatting, data, and colours are preserved as much as possible.
22. Generated worksheet name increments if `Generated Allocation` already exists.
23. Theme-black GLF cells are treated as black-filled passed cells.
24. Generated worksheet clears copied text from black-filled passed cells.
25. Generated worksheet highlights newly allocated cells in blue.
26. Preview records include the GLF section header beside the assessee.
27. Preview records show Ward locations with the ward label in brackets when available.
28. Preview records show OPS locations with the OPS shift label in brackets when available.
29. Output workbook can be downloaded.
30. Separate new-allocation workbook can be downloaded.
31. Separate new-allocation workbook matches the website preview output columns.
32. Frontend allocated preview records can be filtered by selected start and end dates.
33. Frontend shows rostered/available assessors who were not assigned any assessee in the selected date range.

---

## 22. Implementation Notes

Prioritise correctness of allocation logic over UI complexity.

The first version can use a simple frontend.

Focus on:

1. Correct workbook parsing.
2. Correct interpretation of colours.
3. Correct matching between GLF workbook and roster workbook.
4. Correct capacity and round-robin allocation.
5. Correct generated output workbook.

Do not attempt to modify the original progress worksheet.

Only create a new generated worksheet containing allocation results.

---

## 23. Acceptance Criteria

The project is complete when:

1. User can upload both Excel workbooks.
2. User can enter the GLF workbook password.
3. Backend can read the password-protected GLF workbook.
4. Backend reads the first roster worksheet for OPS entries and non-ward GLF availability.
5. Backend reads white cells with a ward value (braces removed before checking) in the first roster worksheet as Ward availability and Ward date/location entries for the row's column A person, while fully ignoring non-ward-only white cells for automatic allocation. Assessment candidates remain the names in column A of the GLF progress worksheet.
6. Backend reads the second worksheet of the GLF workbook for current progress.
7. The system identifies blank assessment cells requiring allocation.
8. The system skips black-filled cells.
9. The system skips existing allocation cells with text.
10. The system ignores CBD and PA.
11. The system matches assessments based on location rules.
12. The system enforces 4 assessments per full day or 2 per half day, with no same-day mixing of assessment groups.
13. The system enforces max 2 MiniCeX per assessor per day.
14. The system uses round-robin allocation among eligible assessors.
15. The system avoids assessors already used for the same assessee in the GLF second worksheet for Rx Check, Dispensing, Med Recon, and MiniCeX where possible, while allowing same-run reuse when capacity permits.
16. The system creates a new worksheet immediately after the first worksheet.
17. The system preserves all original worksheets.
18. The system does not overwrite the original second worksheet.
19. The system outputs the full updated GLF workbook for download.
20. The generated worksheet is a copied progress worksheet with assessor/date values written only into allocated copied cells.
21. The generated worksheet preserves black-filled passed cells and clears copied text from those cells.
22. The generated worksheet highlights newly allocated cells in blue.
23. The frontend shows allocation summary and preview.
24. The frontend preview includes the GLF section header beside each assessee.
25. The frontend preview shows Ward locations with the ward label in brackets when available.
26. The frontend preview shows OPS locations with the OPS shift label in brackets when available.
27. The frontend can filter allocated preview rows by selected start and end dates.
28. The frontend shows assessors who were rostered as GLF/available in the selected date range but were not assigned any assessee.
29. The system outputs a separate new-allocation workbook for download.
30. The separate new-allocation workbook follows the website preview output.
31. Errors are shown clearly to the user.


## Allocation implementation verification

The roster reader accepts a single worksheet and reads only the first worksheet. Column A identifies the person; green cells provide OPS dates, yellow `GLF`/`/GLF`/`GLF/` cells provide full/half-day availability, and white cells containing a two-digit Ward number provide Ward dates and availability. Ward detection searches the whole cell without requiring separators or a suffix, removes braces for classification, and keeps the cell text (including braces, with whitespace normalised) for display. Non-ward-only cells and floater placeholders are excluded.

Allocation tracks total count, MiniCeX count, and assessment group per assessor per date. Grouping preferences apply only after eligibility, capacity, same-day group separation, and existing-history avoidance. Loads reset for each date and each generation. Regression tests cover these rules alongside existing workbook preservation and export tests.


### Requirements reconciliation

AGENTS.md takes precedence over this document. Website and allocation-only export columns are exactly Date, Assessee, Header, Assessment, Location, Assessor, Status, Reason, Cell. Ward labels preserve the white cell text with whitespace normalised; OPS displays as `OPS`. The API returns all records without a 500-record truncation. The UI shows all summary counts and provides skipped/unallocated records with reasons separately from the allocated preview. Excel RGB, indexed and workbook theme fills (including tints) are resolved by shared colour helpers. Name-only assessee rows are included, section headers and legend rows excluded, and compatible roster dates are considered chronologically.
