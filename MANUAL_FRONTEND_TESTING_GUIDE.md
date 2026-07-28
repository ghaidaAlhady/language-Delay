# Manual Frontend Testing Guide

This guide uses the normal development backend and development database. It does not use
the disposable E2E database.

## Start the backend

Open PowerShell and run:

```powershell
cd "C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Expected URLs:

- Backend: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Leave this terminal running.

## Start the frontend

Open a second PowerShell window and run:

```powershell
cd "C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub\frontend"
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`. The frontend's local
configuration must point `VITE_API_BASE_URL` to `http://127.0.0.1:8000`.

## Manual test flow

1. Open the frontend and create a parent account.
2. Sign out, then sign in with the same account.
3. Add a child whose current age is between 2 and 5 years.
4. Open the child profile and start the initial assessment.
5. Answer every question and view the assessment result.
6. Confirm the page uses supportive, non-diagnostic wording and shows referral guidance
   only when the deterministic rules require it.
7. Open the weekly plan and review its activities.
8. Mark activities as completed where appropriate.
9. Start the weekly follow-up through the normal child/profile navigation.
10. Complete the follow-up assessment and view the progress comparison.
11. Open the replacement weekly plan and confirm it is the active plan.
12. Reload the browser and confirm the child, assessment, follow-up, and active plan remain.
13. Sign out, sign back in, and confirm the same data is still available.

Use a clearly fictional test parent and fictional child. Do not enter real child names,
medical history, contact details, or other personal information. Use a unique test email
address that you control or reserve only for local testing. The local development database
persists test data, so do not assume logout removes it.

## Stop the servers

Press `Ctrl+C` in the frontend terminal and then in the backend terminal. Wait until both
commands return to the PowerShell prompt.

Do not use `backend/run_e2e_server.py`, `backend/run_e2e_server.sh`, port `8001`, or
`backend/language_delay_e2e.db` for manual testing. Those are reserved for isolated
automated tests and the database is deleted at E2E startup.

## Troubleshooting

If a port is occupied, identify the listener without stopping unrelated processes:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000
Get-NetTCPConnection -State Listen -LocalPort 5173
```

If port 5173 is occupied, Vite may select another port and print it. Open the printed URL.
If port 8000 is occupied by the intended backend, reuse that server. Otherwise, close the
owning application only after confirming it is safe; do not terminate an unknown process.

If PowerShell blocks virtual-environment activation, the backend can be started without
activation:

```powershell
cd "C:\Users\welcome\Desktop\Smart-Guide-Language-Delay-GitHub\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

For a frontend “cannot connect to server” message:

1. Confirm `http://127.0.0.1:8000/health` returns successfully.
2. Confirm the backend terminal shows no startup error.
3. Confirm the frontend uses `http://127.0.0.1:8000` as its API base URL.
4. Confirm the frontend origin is allowed by the backend CORS configuration.
5. Stop and restart only the two development servers after correcting the issue.

Do not edit or delete the development database as a troubleshooting shortcut.
