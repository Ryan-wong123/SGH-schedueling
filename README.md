# GLF Assessment Scheduler

Web app for generating GLF assessment allocation records from:

- `GLF Assessment Overview.xlsx`
- `Roster Ward Allocation.xlsx`

The GLF workbook password is supplied by the user at upload time. Do not hardcode it in application logic.

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

