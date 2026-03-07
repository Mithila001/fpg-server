# Frontend Agent Instructions

## Port Management (Strict)

- **Primary Port:** This project **must** run on port `5173`.
- **Constraint:** Do not allow Vite to "port hop" to 5174 or others.
- **Conflict Resolution:** 1. If port `5173` is already in use (Ghost/Orphan ports), identify the Process ID (PID) using `netstat -ano | findstr :5173`. 2. Terminate the blocking process immediately using `taskkill /F /PID <PID>`. 3. Once cleared, restart the dev server on `5173`.
- **Config:** Ensure `server.strictPort` is set to `true` in `vite.config.js`.

## Tools & Previewing

- **Internal Browser:** Use the VS Code built-in **Simple Browser** for all UI previews to keep the workflow inside the editor.
- **How to Open:** Use the command palette (`Ctrl+Shift+P`) and search for `Simple Browser: Show`.
- **URL:** Direct the browser to `http://localhost:5173`.

## Development Workflow

- Always check for "CLOSE_WAIT" or "FIN_WAIT" states if the hot-reload feels sluggish.
- If the terminal is unresponsive, kill all Node processes via PowerShell: `Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force`.
