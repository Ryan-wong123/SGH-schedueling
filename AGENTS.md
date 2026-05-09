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
- `TASKS.md` — implementation checklist and task breakdown
- `AGENTS.md` — coding-agent instructions and project conventions

When requirements conflict, follow this priority order:

1. `PRD.md`
2. `ARCHITECTURE.md`
3. `TASKS.md`
4. `AGENTS.md`

---

## High-Level Requirements

The system must:

1. Accept both Excel workbook uploads.
2. Accept the GLF workbook password from the user.
3. Read the password-protected GLF workbook.
4. Use only the first worksheet of the Roster Ward Allocation Workbook.
5. Ignore the second worksheet of the Roster Ward Allocation Workbook.
6. Use the second worksheet of the GLF Assessment Workbook as the current assessment progress worksheet.
7. Allocate assessors only for blank assessment cells in these columns:
   - Rx Check
   - Dispensing
   - Med Recon
   - MiniCeX
8. Skip black-filled cells because they indicate the assessee has passed out of the assessment.
9. Skip cells with existing text because they already contain allocation history.
10. Ignore CBD and PA for automatic allocation.
11. Enforce daily assessor limits:
    - Maximum 4 total assessments per assessor per day
    - Maximum 2 MiniCeX assessments per assessor per day
12. Use round-robin allocation among eligible assessors.
13. Avoid assigning the same assessor already used for the same assessee for MiniCeX and Med Recon, where possible.
14. Generate a new worksheet named `Generated Allocation`.
15. Insert the generated worksheet immediately after the first worksheet.
16. Preserve all existing worksheets, formulas, formatting, data, and colours as much as possible.
17. Do not overwrite the original second worksheet.
18. Return the full updated GLF workbook for download.

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

- Use only the first worksheet.
- Yellow GLF cells identify full-day available assessors.
- Green cells indicate OPS.
- White, purple, orange, and beige cells indicate Ward.

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
Rx Check + Dispensing + Med Recon + MiniCeX <= 4
MiniCeX <= 2
```

Round-robin selection:

1. Filter eligible assessors by date, GLF availability, location, and capacity.
2. Pick the eligible assessor with the fewest assignments for that date.
3. If tied, pick the assessor least recently used.
4. If still tied, sort by assessor name alphabetically.

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
- Cell colour classification
- Assessment cell status classification
- Capacity rules
- MiniCeX limit
- Location compatibility
- Round-robin assignment
- Output worksheet creation
- Worksheet preservation

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
