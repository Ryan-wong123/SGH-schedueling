# GLF Assessment Scheduler

Web app for generating GLF assessment allocation records from:

- `GLF Assessment Overview.xlsx`
- `Roster Ward Allocation.xlsx`

The GLF workbook password is supplied by the user at upload time. Do not hardcode it in application logic.

After processing, the app provides two downloads:

- The full updated GLF workbook with a generated allocation worksheet inserted.
- A separate `GLF_New_Allocation.xlsx` workbook matching the website preview output for newly allocated records.

## Backend

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open local app:

```text
http://127.0.0.1:5173
```

## Easy Start

On Windows, double-click:

```text
Run GLF Scheduler.bat
```

The launcher will:

- create the Python virtual environment if it is missing
- install backend Python packages
- install frontend packages if needed
- start the backend and frontend in separate windows
- open the app at `http://127.0.0.1:5173`

Keep the backend and frontend windows open while using the app. Close those windows when finished.

## Build A Standalone Windows `.exe`

Run this on the build computer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-exe.ps1
```

The build computer needs Python and Node.js/npm installed. The computers that run the finished app do not.

The finished executable is created at:

```text
dist\GLF Assessment Scheduler.exe
```

Copy that `.exe` to another Windows computer and double-click it. It starts the local scheduler server and opens the app in the browser.

