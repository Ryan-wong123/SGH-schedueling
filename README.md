# GLF Scheduler

GLF Scheduler is a small local web application that fills pending GLF assessment assignments into an uploaded GLF assessment workbook. It uses two Excel workbooks:

- a roster ward allocation workbook
- a GLF assessment overview workbook

The app reads who is working, where they are assigned, which assessments are still due, and then downloads a new copy of the GLF assessment workbook with assessor/date values filled into the correct assessment cells.

## How The Application Works

The application runs as a local Python web server at `http://127.0.0.1:8000`.

1. The browser loads `static/index.html`.
2. The user uploads the roster workbook and the GLF assessment overview workbook.
3. The frontend sends both files to `POST /api/schedule`.
4. `app.py` loads both Excel files.
5. The roster workbook is parsed into daily staff availability:
   - ward assignments
   - OPS availability
   - GLF duty days
   - working or non-working status
6. The GLF overview workbook is read from its second worksheet using fixed assessment columns:
   - Mini-CEX
   - CBD
   - Med Recon
   - Dispensing
   - Rx Check
7. Blank cells in the assessment columns are treated as assessment tasks that need an assessor to be allocated to them.
8. Blacked-out assessment cells are treated as already completed and are skipped.
9. Assessment cells that contain an assessor name and date are treated as already assigned or previously assessed, and that assessor is excluded from future assignments for the same student.
10. The scheduler assigns each task to the best available assessor based on GLF availability, matching activity/location, daily workload limits, and round-robin distribution.
11. The download button will download the updated GLF workbook with the updated assessors with its date using the same format as the GLF workbook's second worksheet.

## Scheduling Rules

The scheduling logic is defined in `app.py`.

- Mini-CEX and Med Recon require the assessee to be on a ward.
- Dispensing requires the assessee to be in OPS.
- CBD and Rx Check can be scheduled when the assessee has a usable working location.
- Assessors cannot assess themselves.
- The student and assessor must both be marked `GLF` on the same date in the roster workbook.
- The student and assessor must have matching activity/location:
  - ward assessments require an overlapping ward assignment
  - OPS assessments require both people to be in OPS
  - general assessments require either an overlapping ward or both people in OPS
- Assessors already listed in columns `G:K` for the same student are excluded from future assignments for that student.
- During the same generated schedule, the app prefers assessors who have not already been assigned to that student.
- Each assessor can receive up to 4 assessments per day.
- Each assessor can receive up to 2 Mini-CEX assessments per day.
- Overall assessor load is balanced so eligible assessors get turns as evenly as possible where the GLF/date/location constraints allow it.


## Running The App

From the project folder:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

Upload:

- `7.Roster Ward Allocation(13Apr-8May26) .xlsx`
- `GLF Assessment Overview 2024_updated.xlsx`

If the GLF workbook is encrypted, enter its password in the password field before generating the schedule.



## Workbook Parsing Notes

The roster parser expects date headers near the top of each sheet.

For roster sheets with `ward` in the sheet name, such as `Ward_13Apr26-8May26`, the first column is treated as the ward name and the dated columns are scanned for staff names. This provides ward-location matching.

For other roster sheets, such as `Roster_13Apr26-8May26`, the first column is treated as the staff name. Dated cells are used to detect whether the person is working, in OPS, or marked for GLF.

The GLF overview parser always reads the second worksheet in the workbook. Other GLF workbook sheets are ignored. On that second sheet, column `A` is treated as the student name. Columns `G`, `H`, `I`, `J`, and `K` are treated as the five assessment columns. If assessment headers are found in the first 40 rows, they are used to label those columns; otherwise, the default order is Mini-CEX, CBD, Med Recon, Dispensing, and Rx Check.

Cells in `G:K` are skipped when they are black-filled or marked as completed, passed, done, exempt, or not applicable. Cells that contain an assessor name and date are also skipped as already assigned, and the assessor name is remembered so the same student is not assigned back to that assessor.

## Scheduling Output Logic

For each pending task, the scheduler searches the roster dates for a student/assessor pair where:

- the student is marked `GLF` on that date
- the assessor is marked `GLF` on that date
- both people have the required matching activity/location
- the assessor is not the student
- the assessor has not already assessed that student in the GLF assessment workbook
- the assessor is within the daily assessment limits

When multiple assessors are eligible, the scheduler prefers assessors with lower total assigned load and avoids giving the same student the same assessor again where possible.

