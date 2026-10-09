# AGENTS.md

## Project Context

This repository is for the **GLF Assessment Scheduler Website**.

The project builds a web application that accepts two Excel workbooks:

1. **GLF Assessment Workbook**
2. **Roster Ward Allocation Workbook**

The system reads assessment progress and roster availability, then generates assessment allocation records for:

- Rx Check
- Dispensing
- Med Recon
- MiniCeX

The GLF Assessment Workbook is password protected. The website must ask the user for the password before reading the workbook.

For local testing, the sample password is:

```text
coreassessor
```

Do not hardcode this password in production logic.

---

## Primary Reference Files

Codex should use these project markdown files as the source of truth:

- `PRD.md` — product requirements and business rules
- `ARCHITECTURE.md` — technical design and system structure
- `AGENTS.md` — coding-agent instructions and project conventions

When requirements conflict, follow this priority order:

1. `AGENTS.md` 
2. `PRD.md`
3. `ARCHITECTURE.md`

Update the `PRD.md` and `ARCHITECTURE.md` whenever something is changed or implemented.

---

## High-Level Requirements

The system must:

1. Accept both Excel workbook uploads.
2. Accept the GLF workbook password from the user.
3. Read the password-protected GLF workbook.
4. Use the first worksheet of the Roster Ward Allocation Workbook for OPS entries (Rx Check & Dispensing) which uses cells that are green in color.
5. Use the first worksheet of the Roster Ward Allocation Workbook for Ward entries (miniCeX & Med Recon) which uses the cells that are in white color.
   - Do not rely on separators. Values in a cell may be split by line breaks, commas, slashes or spaces, or written together with no separator at all.
   - A ward value is a two-digit ward number, usually followed by a letter, suffix or bracketed bed range (e.g. `11B`, `45A`, `58 ISO`, `58ISO`, `63(12-14)`, `68ICU`, `46B1,C`). Search the whole cell text for one, wherever it appears.
   - Everything else is a non-ward value, e.g. Admin, LTX, MICU, Burns, MICA, CTS, IPAS/IDD, MSF (2-5), DI, SGH@Home Command Centre, WR - RS, WR - IM, WR - AMW, Clinic-1, Clinic-2/RTxC, INF, HDL, MIC, NICU-1, SB, DD, /oc, vl. Single-digit numbers inside these (`NICU-1`, `Clinic-2`, `MSF (2-5)`, `MIC2`) are not ward numbers.
   - If a white cell contains no ward value, exclude the whole cell from Ward allocation (e.g. `CTS`, `DI`, `MICU / Burns`, `IPAS/IDD / MSF (2-5)`).
   - If a white cell contains at least one ward value, use the cell for Ward allocation even if it also contains non-ward values (e.g. `45A / MICA`, `75B/C / SB`, `45AMICA`).
   - Braces `{...}` are ignored: remove the `{` and `}` characters and classify the text inside like any other value. `{45A}` is a ward value; `{ACC1}`, `{NICU-1}`, `{CVM}`, `{CICU}` are non-ward values. So `{45A}` and `67A / {CICU}` are used, while `{CICU}` alone is excluded.
6. Use the second worksheet of the GLF Assessment Workbook as the current assessment progress worksheet.
7. Preserve the GLF section header above each assessee row for the website preview table.
8. Allocate assessors only for blank assessment cells in these columns:
   - Rx Check
   - Dispensing
   - Med Recon
   - MiniCeX
9. For GLF Assessment Workbook, skip black-filled cells because they indicate the assessee has passed out of the assessment.
10. For GLF Assessment Workbook, skip cells with existing text because they already contain allocation history.
11. For GLF Assessment Workbook, ignore CBD and PA columns for allocation.
12. Enforce daily assessor limits:
    - Maximum 4 total assessments per assessor per day on a Full day GLF (`GLF`)
    - Maximum 2 total assessments per assessor per day on a Half day GLF (`/GLF` or `GLF/`)
    - Maximum 2 MiniCeX assessments per assessor per day
    - An assessor cannot do MiniCeX or Med Recon on the same day as Rx Check (prescription check) or Dispensing. Each assessor's day is either a MiniCeX/Med Recon day or an Rx Check/Dispensing day, never both.
    - Where possible, group an assessor's assessments for the day: prefer giving MiniCeX and Med Recon together, or Rx Check and Dispensing together (for example, the same assessee's MiniCeX and Med Recon to the same assessor on the same day).
13. Use round-robin allocation among eligible assessors.
14. Never select a person listed in column A of the GLF progress worksheet as an assessor, including shortened roster-name variants.
15. Never assign an assessee to themself, including shortened roster-name variants.
16. Avoid assigning the same assessor already used for the same assessee in the GLF second worksheet for Rx Check, Dispensing, Med Recon, and MiniCeX, where possible.
    New allocations created during the current generation may reuse the same assessor for the same assessee when that assessor still has capacity under the daily limits.
17. Show Ward locations in the website preview as `Ward (<ward location>)` when the Ward location label is available.
18. Generate a new worksheet named `Generated Allocation`.
19. Insert the generated worksheet immediately after the first worksheet.
20. Preserve all existing worksheets, formulas, formatting, data, and colours as much as possible.
21. Do not overwrite the original second worksheet.
22. Return the full updated GLF workbook for download.
23. Return a separate new-allocation workbook for download, matching the website preview output.

---

## Tech Stack Instructions

Use the following stack unless the user explicitly asks for another stack.

### Backend

- Python
- FastAPI
- openpyxl
- msoffcrypto-tool or equivalent for password-protected Excel reading
- pytest for tests

### Frontend

- React
- TypeScript
- Simple CSS or component-level styling

Avoid overengineering the UI. Correct workbook parsing and allocation logic are more important than visual design.

---

## Coding Standards

### General

- Write clear, maintainable code.
- Prefer small functions with single responsibilities.
- Keep business rules out of route handlers.
- Put allocation logic in services.
- Put workbook parsing logic in parser modules.
- Put colour classification in utility modules.
- Use typed models where practical.
- Add comments only where the logic is non-obvious.

### Python

- Use type hints for service-layer functions.
- Use dataclasses or Pydantic models for structured data.
- Keep FastAPI routes thin.
- Raise clear validation errors.
- Avoid global mutable state for allocation state.
- Use temporary files for upload processing.
- Clean up temporary files after processing where possible.

### TypeScript / React

- Use TypeScript interfaces for API responses.
- Keep upload and results components separated.
- Show clear loading and error states.
- Do not hide backend validation errors.
- Keep API calls in a dedicated client module.

---

## Excel Handling Rules

### Important

Excel formatting is part of the business logic.

The system must inspect cell fill colours, not only cell values.

### GLF Workbook

- Second worksheet is the current progress worksheet.
- Black-filled assessment cells mean passed out / skip.
- Blank assessment cells mean allocation needed.
- Cells with text mean already allocated / skip.
- CBD and PA columns must be ignored.

### Roster Workbook

- Use the first worksheet for everything: OPS entries, GLF availability, and Ward allocation. Other roster worksheets are not read.
- In the first worksheet, each row is a person (name in column A) and each date column holds that person's location for the day.
- Green cells in the first worksheet indicate OPS.
- Yellow colored cells with the value "GLF" in the first worksheet identify assessors available for allocation.
- White cells in the first worksheet are Ward cells, filtered in this order:
  1. Remove any `{` and `}` characters, then ignore white cells with no ward value (see High-Level Requirement 5).
  2. Remaining white cells create a Ward availability and a Ward date/location entry for the person in column A of that row. Assessment candidates remain the people in column A of the second GLF workbook worksheet, and those names must not be selected as assessors.
- The Ward location label is the full text of the white Ward cell itself, keeping any `{` and `}` characters (e.g. `45A MICA`, `67A {CICU}`). Braces are removed only when checking for a ward value.
- Ignore `floater` / `*floater*` roster placeholders.
- Ignore non-white, non-green, non-yellow cells for allocation.

Because Excel colours may appear as RGB, indexed, or theme colours, create tolerant helper functions for colour detection.

---

## Allocation Rules

Assessment location compatibility:

| Assessment | Location |
|---|---|
| Rx Check | Ward or OPS |
| Dispensing | OPS only |
| Med Recon | Ward only |
| MiniCeX | Ward only |

Assessor capacity:

```text
Full day GLF:  Rx Check + Dispensing + Med Recon + MiniCeX <= 4
Half day GLF:  Rx Check + Dispensing + Med Recon + MiniCeX <= 2
MiniCeX <= 2
Same day: (MiniCeX or Med Recon) and (Rx Check or Dispensing) never mixed for one assessor
```

Round-robin selection:

1. Filter eligible assessors by date, GLF availability, location, capacity, and same-day assessment grouping.
2. Prefer an eligible assessor who already has assessments from the same group (MiniCeX/Med Recon or Rx Check/Dispensing) that day, ideally for the same assessee.
3. Then pick the eligible assessor with the fewest assignments for that date.
4. If tied, pick the assessor least recently used.
5. If still tied, sort by assessor name alphabetically.

---

## Output Workbook Rules

The output workbook must:

1. Be based on the original GLF Assessment Workbook.
2. Preserve all original worksheets.
3. Insert a new worksheet immediately after the first worksheet.
4. Name the worksheet `Generated Allocation`.
5. If the name already exists, use `Generated Allocation 2`, `Generated Allocation 3`, etc.
6. Not overwrite or delete the original second worksheet.
7. Preserve data, formulas, formatting, and colours as much as possible.
8. Copy the original GLF progress worksheet as the generated worksheet.
9. Write assessor/date text only into successfully allocated copied assessment cells.
10. Highlight successfully allocated copied assessment cells in blue.
11. Do not write skipped or unallocated records into copied assessment cells.
12. Clear copied values from black-filled passed cells while preserving the black fill.

The website must also generate a separate allocation-only workbook:

1. Name the worksheet `New Allocation`.
2. Include only successfully allocated records.
3. Use the same display columns as the website preview table:
   - Date
   - Assessee
   - Header
   - Assessment
   - Location
   - Assessor
   - Status
   - Reason
   - Cell
4. Preserve display-ready Ward locations as `Ward (<ward location>)`.
5. Offer this file as a separate download from the full updated GLF workbook.

---

## Website Preview Table

The website preview table must:

1. Show a `Header` column beside `Assessee`.
2. Populate `Header` from the most recent GLF section header above the assessee row, such as `Y10`, `Y7`, `Y1`, or `New Pre-reg > OPRs`.
3. Show Ward locations as `Ward (<ward location>)` when a Ward location label is available from the roster workbook.
4. Match the separate new-allocation workbook columns for allocated records.
5. Continue to show OPS locations as `OPS`.

---

## Error Handling Expectations

Return clear errors for:

- Missing GLF workbook
- Missing roster workbook
- Empty password
- Wrong GLF password
- Invalid Excel file
- Missing worksheet
- Missing required columns
- Unable to detect GLF availability
- Unable to classify location
- No eligible assessor found
- Unexpected workbook parsing failure

Do not silently fail.

---

## Testing Expectations

When implementing or modifying the system, add or update tests for:

- Workbook password handling
- GLF second worksheet parsing
- Roster first worksheet parsing
- Roster first worksheet Ward parsing from white cells
- Braces are removed from Ward cells and the inner text is classified as ward or non-ward like any other value
- White cells with no ward value are excluded; white cells mixing ward and non-ward values are used
- Ward assessor selection from first worksheet white cells
- GLF section header extraction for preview records
- Ward location label extraction for preview records
- Cell colour classification
- Theme-black GLF cell classification
- Assessment cell status classification
- Capacity rules
- MiniCeX limit
- Half day GLF limit of 2 assessments
- MiniCeX/Med Recon never mixed with Rx Check/Dispensing for one assessor on the same day
- Preference for grouping MiniCeX with Med Recon, and Rx Check with Dispensing
- Location compatibility
- Round-robin assignment
- Output worksheet creation
- Blue highlight on newly allocated copied assessment cells
- Worksheet preservation
- Separate new-allocation workbook generation
- Separate new-allocation workbook preview columns

---

## What Not To Do

Do not:

- Hardcode row numbers unless unavoidable.
- Hardcode the GLF password into core logic.
- Modify the original GLF progress worksheet.
- Delete or overwrite existing worksheets.
- Allocate CBD or PA.
- Treat section headers as assessees.
- Ignore cell colours.
- Store uploaded files permanently.
- Put allocation logic directly inside FastAPI route functions.
