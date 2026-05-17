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
- Download button for generated workbook

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
7. User can download the updated GLF workbook.

---

## 4. Input File 1: Roster Ward Allocation Workbook

### 4.1 Workbook Rule

The Roster Ward Allocation Workbook contains 2 worksheets.

Use the first worksheet for OPS entries and non-ward GLF availability.

Use the second worksheet for Ward allocation.

The first worksheet contains OPS schedule information and non-ward GLF assessor availability.

The second worksheet contains Ward allocation information and must be used for Ward assessees and Ward assessors.

### 4.2 GLF Availability Rule

In the first worksheet of the roster workbook:

- Rows with the `GLF` cell highlighted yellow are assessors who are free for the whole day.
- These assessors are eligible to perform non-ward assessments for assessees on that GLF availability date.

The system must identify assessors with GLF availability by reading the cell fill colour.

For Ward allocation, the system must use the second worksheet:

- Only white-filled cells are used.
- Names outside `{...}` are Ward assessors available on that date.
- Names inside `{...}` are Ward assessees available on that date.
- `floater` / `*floater*` text is a roster placeholder and must not be treated as an assessor or assessee.
- Non-white cells in the second worksheet must be ignored for Ward allocation.

### 4.3 Location Colour Rule

Inside the roster worksheet, colour-coded cells represent different assessment locations.

The system must read the Excel cell fill colour to determine location.

Use the following location rules:

| Colour / Cell Type | Meaning |
|---|---|
| Green cells in worksheet 1 | OPS |
| White cells in worksheet 2 | Ward |
| Non-white cells in worksheet 2 | Ignore for Ward allocation |

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
5. Round-robin balancing

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

For MiniCeX and Med Recon:

- Avoid assigning the same assessor already used for that assessee from the second worksheet.
- The system should read existing MiniCeX and Med Recon cells for that assessee and avoid repeating the same assessor if possible.

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

Each assessor can only be assigned a maximum of 4 assessments per day.

Each assessor can only be assigned a maximum of 2 MiniCeX assessments per day.

Use these rules programmatically:

```text
Rx Check + Dispensing + Med Recon + MiniCeX <= 4
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
| 1 | 1 | 1 | 1 |
| 2 | 1 | 1 | 0 |
| 1 | 0 | 2 | 1 |
| 0 | 1 | 1 | 2 |

Invalid examples:

| Rx Check | Dispensing | Med Recon | MiniCeX | Reason |
|---:|---:|---:|---:|---|
| 2 | 1 | 1 | 1 | Total is 5 assessments |
| 0 | 0 | 1 | 3 | MiniCeX exceeds 2 |

---

## 7. Round-Robin Allocation Rule

Use round-robin allocation among eligible assessors so that the same assessor is not always scheduled for every assessment.

For each assessment date:

1. Maintain a rotating list of available assessors.
2. Filter assessors by GLF availability.
3. Filter assessors by location compatibility.
4. Filter assessors by daily capacity.
5. Always assign the eligible assessor with the lowest number of assignments for that date.
6. If tied, assign the assessor who was least recently used.
7. If still tied, sort by assessor name alphabetically.

### 7.1 Capacity Check During Round-Robin

Before assigning an assessor, check:

```text
assessor_total_assignments_for_date < 4
```

For MiniCeX, also check:

```text
assessor_minicex_assignments_for_date < 2
```

### 7.2 Repeat Assessor Avoidance

For MiniCeX and Med Recon:

- Avoid assigning the same assessor already used for that assessee in the GLF second worksheet.
- If all eligible assessors were already used before, choose the least recently used eligible assessor and mark the reason as:

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

### Step 3: Parse Roster

1. Open the first worksheet of the roster workbook for OPS entries and non-ward GLF availability.
2. Open the second worksheet of the roster workbook for Ward allocation.
3. Detect non-ward assessors with yellow GLF availability in worksheet 1.
4. Detect OPS assessee date and location from green cells in worksheet 1.
5. Detect Ward assessors and Ward assessees from white cells in worksheet 2.
6. Ignore non-white cells in worksheet 2 for Ward allocation.
7. Classify locations:
   - Green cells in worksheet 1 = OPS
   - White cells in worksheet 2 = Ward

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
   - MiniCeX/Med Recon repeat-assessor rule
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
- For `Skipped - Already Passed` records, leave the copied cell black-filled and clear any copied text value.
- For `Skipped - Already Allocated` records, preserve the existing copied assessor/date text.
- For `Unallocated` records, leave the copied cell blank.
- Do not modify the original GLF progress worksheet.

The backend API response should still return allocation records for preview in the frontend, including:

- Date
- Assessee Name
- Assessment Type
- Assessee Location
- Assigned Assessor
- Assessor GLF Availability Date
- Status
- Reason if Unallocated or Skipped
- Original GLF Cell Reference
- Existing Allocation History

### 10.1 Status Values

Use only these status values:

| Status | Meaning |
|---|---|
| Allocated | A valid assessor was assigned |
| Unallocated | No valid assessor could be found |
| Skipped - Already Passed | The assessment cell is black-filled |
| Skipped - Already Allocated | The assessment cell already contains assessor/date text |
| Skipped - Not Applicable | The row or cell should not be automatically scheduled |
| Skipped - Unsupported Cell State | The cell colour or state is unclear |

### 10.2 Example API Preview Rows

| Date | Assessee Name | Assessment Type | Assessee Location | Assigned Assessor | Assessor GLF Availability Date | Status | Reason if Unallocated or Skipped | Original GLF Cell Reference | Existing Allocation History |
|---|---|---|---|---|---|---|---|---|---|
| 10/03/26 | Amanda Chua Jing Yi | Rx Check | Ward | Cheryl | 10/03/26 | Allocated |  | G45 |  |
| 15/04/26 | Celine Sia Si Lin | Med Recon | Ward | Gen | 15/04/26 | Allocated |  | I46 |  |
| 08/04/26 | Chan Xiao Ting, Kristy | MiniCeX | Ward |  |  | Skipped - Already Allocated | Existing allocation found | J47 | Cheryl 08/04/26 |
| 22/04/26 | Megan Goh | Dispensing | OPS |  |  | Unallocated | No available assessor with OPS-compatible availability | H23 |  |
|  | Denise Song | Rx Check |  |  |  | Skipped - Already Passed | Black-filled cell | G23 |  |

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

### 11.4 Error Display

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
  "download_id": "string"
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
  assessmentType: AssessmentType;
  assesseeLocation: LocationType;
  assignedAssessor: string;
  assessorGlfAvailabilityDate: string;
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
| White on worksheet 2 | Ward location for assessors and assessees |
| Non-white on worksheet 2 | Ignore for Ward allocation |

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
3. Roster workbook has at least 2 worksheets.
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
The roster workbook must contain at least two worksheets.
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
2. Roster workbook uses the first worksheet for OPS/non-ward availability and the second worksheet white cells for Ward assessors and assessees.
3. GLF workbook uses the second worksheet as progress source.
4. Black-filled GLF cells are skipped.
5. Blank GLF assessment cells are considered for allocation.
6. Existing text cells are skipped.
7. CBD and PA columns are ignored.
8. MiniCeX and Med Recon avoid repeated assessors for the same assessee.
9. Assessor max 4 assessments per day is enforced.
10. Assessor max 2 MiniCeX per day is enforced.
11. Dispensing only matches OPS.
12. MiniCeX only matches Ward.
13. Med Recon only matches Ward.
14. Rx Check matches Ward or OPS.
15. Round-robin chooses the least-assigned eligible assessor.
16. New worksheet is inserted after the first worksheet.
17. Existing second worksheet is preserved and shifted.
18. Existing worksheets, formulas, formatting, and colours are preserved as much as possible.
19. Generated worksheet name increments if `Generated Allocation` already exists.
20. Theme-black GLF cells are treated as black-filled passed cells.
21. Generated worksheet clears copied text from black-filled passed cells.
22. Output workbook can be downloaded.

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
5. Backend reads the second roster worksheet white cells for Ward assessors and assessees.
6. Backend reads the second worksheet of the GLF workbook for current progress.
7. The system identifies blank assessment cells requiring allocation.
8. The system skips black-filled cells.
9. The system skips existing allocation cells with text.
10. The system ignores CBD and PA.
11. The system matches assessments based on location rules.
12. The system enforces max 4 assessments per assessor per day.
13. The system enforces max 2 MiniCeX per assessor per day.
14. The system uses round-robin allocation among eligible assessors.
15. The system avoids repeated assessors for MiniCeX and Med Recon where possible.
16. The system creates a new worksheet immediately after the first worksheet.
17. The system preserves all original worksheets.
18. The system does not overwrite the original second worksheet.
19. The system outputs the full updated GLF workbook for download.
20. The generated worksheet is a copied progress worksheet with assessor/date values written only into allocated copied cells.
21. The generated worksheet preserves black-filled passed cells and clears copied text from those cells.
22. The frontend shows allocation summary and preview.
23. Errors are shown clearly to the user.
