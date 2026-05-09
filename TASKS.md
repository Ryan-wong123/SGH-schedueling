# TASKS.md

## Implementation Plan

Use this checklist to build the GLF Assessment Scheduler Website incrementally.

Do not try to implement everything in one large change. Complete the project in small, testable phases.

---

## Phase 1: Project Setup

### Backend Setup

- [ ] Create `backend/` folder.
- [ ] Create FastAPI application.
- [ ] Add `requirements.txt`.
- [ ] Install backend dependencies:
  - `fastapi`
  - `uvicorn`
  - `python-multipart`
  - `openpyxl`
  - `msoffcrypto-tool`
  - `pytest`
  - `httpx`
- [ ] Create `GET /health` endpoint.
- [ ] Add basic backend test for health endpoint.

### Frontend Setup

- [ ] Create `frontend/` folder.
- [ ] Set up React with TypeScript.
- [ ] Create base `App.tsx`.
- [ ] Create basic CSS.
- [ ] Add API client module.
- [ ] Confirm frontend can call backend health endpoint.

---

## Phase 2: Backend File Upload API

- [ ] Create `POST /api/generate-allocation` endpoint.
- [ ] Accept multipart form data:
  - `glf_workbook`
  - `roster_workbook`
  - `glf_password`
- [ ] Validate both files are present.
- [ ] Validate password is not empty.
- [ ] Validate uploaded files have `.xlsx` extension.
- [ ] Save uploads to temporary storage.
- [ ] Return placeholder JSON response.
- [ ] Add API tests for missing files and missing password.

---

## Phase 3: Password-Protected GLF Workbook Reading

- [ ] Implement `excel_reader.py`.
- [ ] Add function to read normal workbook using `openpyxl`.
- [ ] Add function to read password-protected GLF workbook using the user-entered password.
- [ ] Return clear error if password is wrong.
- [ ] Validate GLF workbook has at least 2 worksheets.
- [ ] Validate roster workbook has at least 1 worksheet.
- [ ] Add tests for successful GLF workbook loading.
- [ ] Add tests for wrong password handling.

---

## Phase 4: Utility Functions

### Name Utilities

- [ ] Implement `normalize_name()`.
- [ ] Implement `names_match()`.
- [ ] Test trimming whitespace.
- [ ] Test case-insensitive matching.
- [ ] Test repeated-space collapse.

### Date Utilities

- [ ] Implement `parse_date()`.
- [ ] Support Excel date values.
- [ ] Support text dates such as `10/3/26`, `10/03/26`, `22/4/26`.
- [ ] Implement `format_date()` as `DD/MM/YY`.
- [ ] Add tests for date parsing and formatting.

### Colour Utilities

- [ ] Implement helper to extract cell fill value.
- [ ] Implement `is_black_fill()`.
- [ ] Implement `is_yellow_fill()`.
- [ ] Implement `is_green_fill()`.
- [ ] Implement `is_ward_fill()`.
- [ ] Implement `classify_location_from_fill()`.
- [ ] Add tests using sample workbook cells where possible.
- [ ] Make colour detection tolerant of RGB, indexed, and theme colours where practical.

---

## Phase 5: GLF Workbook Parser

- [ ] Implement `glf_parser.py`.
- [ ] Always read the second worksheet.
- [ ] Locate assessment columns:
  - Rx Check
  - Dispensing
  - Med Recon
  - MiniCeX
- [ ] Ignore CBD and PA.
- [ ] Identify assessee rows.
- [ ] Ignore section headers:
  - Y1
  - Y2
  - New Pre-reg > OPRs
  - Legend
- [ ] For each assessee row, inspect assessment cells.
- [ ] Classify blank cells as needing allocation.
- [ ] Classify black-filled cells as `Skipped - Already Passed`.
- [ ] Classify text cells as `Skipped - Already Allocated`.
- [ ] Preserve original GLF cell references, such as `G45`.
- [ ] Extract existing allocation history from text cells.
- [ ] Add parser tests for all classification states.

---

## Phase 6: Roster Workbook Parser

- [ ] Implement `roster_parser.py`.
- [ ] Always read only the first worksheet.
- [ ] Ignore the second worksheet and any other worksheets.
- [ ] Detect assessors with yellow GLF availability.
- [ ] Extract assessor names and GLF availability dates.
- [ ] Detect assessee rows and roster dates.
- [ ] Detect location from colour-coded cells:
  - Green = OPS
  - White / Purple / Orange / Beige = Ward
- [ ] Return structured roster data.
- [ ] Add tests to confirm only first worksheet is used.
- [ ] Add tests for GLF availability detection.
- [ ] Add tests for OPS/Ward location detection.

---

## Phase 7: Data Models

- [ ] Create backend allocation models.
- [ ] Add `AssessmentType` model or enum.
- [ ] Add `LocationType` model or enum.
- [ ] Add `AllocationStatus` model or enum.
- [ ] Add `AllocationRecord` dataclass or Pydantic model.
- [ ] Add `GlfAssessmentNeed` model.
- [ ] Add `RosterData` model.
- [ ] Add tests for model serialization if using Pydantic.

---

## Phase 8: Allocation Engine

- [ ] Implement `allocation_service.py`.
- [ ] Match assessees from GLF parser to roster parser using normalized names.
- [ ] Enforce assessment location rules:
  - Rx Check = Ward or OPS
  - Dispensing = OPS only
  - Med Recon = Ward only
  - MiniCeX = Ward only
- [ ] Enforce assessor max 4 assessments per day.
- [ ] Enforce assessor max 2 MiniCeX per day.
- [ ] Implement repeat-assessor avoidance for MiniCeX and Med Recon.
- [ ] Implement round-robin selection:
  - Fewest assignments on date
  - Least recently used
  - Alphabetical tie-break
- [ ] Generate `Allocated` records.
- [ ] Generate `Unallocated` records with clear reasons.
- [ ] Preserve skipped records from GLF parser.
- [ ] Add tests for all allocation rules.

---

## Phase 9: Workbook Writer

- [ ] Implement `workbook_writer.py`.
- [ ] Create new worksheet named `Generated Allocation`.
- [ ] If sheet exists, create `Generated Allocation 2`, `Generated Allocation 3`, etc.
- [ ] Insert generated worksheet immediately after the first worksheet.
- [ ] Preserve original second worksheet and all other worksheets.
- [ ] Write table headers:
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
- [ ] Write all allocation records.
- [ ] Add basic formatting to generated worksheet headers.
- [ ] Save workbook to temporary output path.
- [ ] Add tests for worksheet creation.
- [ ] Add tests for worksheet order.
- [ ] Add tests for sheet name incrementing.

---

## Phase 10: Download Handling

- [ ] Generate unique `download_id` after successful allocation.
- [ ] Temporarily store generated workbook path mapped to `download_id`.
- [ ] Implement `GET /api/download/{download_id}`.
- [ ] Return generated workbook as `.xlsx`.
- [ ] Use filename `GLF_Assessment_Generated_Allocation.xlsx`.
- [ ] Handle invalid or expired download IDs.
- [ ] Clean up old generated files where possible.

---

## Phase 11: Frontend Upload Page

- [ ] Create `UploadForm.tsx`.
- [ ] Add GLF workbook file input.
- [ ] Add roster workbook file input.
- [ ] Add GLF password input.
- [ ] Add `Generate Allocation` button.
- [ ] Validate required fields before submit.
- [ ] Show loading state while processing.
- [ ] Show error message if backend returns an error.

---

## Phase 12: Frontend Results View

- [ ] Create `ResultsSummary.tsx`.
- [ ] Show allocated count.
- [ ] Show unallocated count.
- [ ] Show skipped count.
- [ ] Create `ResultsTable.tsx`.
- [ ] Show preview records.
- [ ] Include status and reason columns.
- [ ] Highlight unallocated records visually.
- [ ] Add download button.
- [ ] Wire download button to `/api/download/{download_id}`.

---

## Phase 13: End-to-End Testing

- [ ] Test full upload flow using sample GLF workbook and roster workbook.
- [ ] Confirm password-protected GLF workbook can be read.
- [ ] Confirm wrong password returns friendly error.
- [ ] Confirm generated worksheet is inserted after first worksheet.
- [ ] Confirm original second worksheet is preserved.
- [ ] Confirm CBD and PA are ignored.
- [ ] Confirm black cells are skipped.
- [ ] Confirm blank cells are considered for allocation.
- [ ] Confirm existing text cells are skipped.
- [ ] Confirm generated workbook downloads correctly.

---

## Phase 14: Polish and Cleanup

- [ ] Improve user-facing error messages.
- [ ] Add README setup instructions.
- [ ] Add backend run command.
- [ ] Add frontend run command.
- [ ] Add test command instructions.
- [ ] Remove debug logs.
- [ ] Ensure passwords are never logged.
- [ ] Ensure uploaded file contents are not logged.
- [ ] Review code for duplicated logic.
- [ ] Confirm all tests pass.

---

## Minimum Viable Product Checklist

The MVP is complete when all these are true:

- [ ] User can upload both `.xlsx` files.
- [ ] User can enter GLF workbook password.
- [ ] Backend reads the protected GLF workbook.
- [ ] Backend reads the roster workbook.
- [ ] Backend identifies assessment cells requiring allocation.
- [ ] Backend applies capacity and location rules.
- [ ] Backend generates allocation records.
- [ ] Backend creates new `Generated Allocation` worksheet.
- [ ] Backend preserves all original worksheets.
- [ ] User can download the updated workbook.
- [ ] Frontend shows summary and preview records.

---

## Stretch Goals

Only attempt these after the MVP works.

- [ ] Add drag-and-drop file upload.
- [ ] Add filter by status in results table.
- [ ] Add export of allocation preview as CSV.
- [ ] Add manual override before generating workbook.
- [ ] Add better colour-mapping configuration screen.
- [ ] Add fuzzy matching suggestions for unmatched names.
- [ ] Add audit log worksheet.
- [ ] Add option to regenerate allocation excluding specific assessors.
