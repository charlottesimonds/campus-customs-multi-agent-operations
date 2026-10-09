# Campus Customs Operations Desk (frontend)

React + TypeScript + Vite dashboard for supervising the Campus Customs agent team. It talks only to the FastAPI backend (Problem 7); it never touches the database.

## Run

The backend must be running first (from `backend/`: `uvicorn main:app --reload --port 8000`, inside the project's `.venv`).

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

The backend URL defaults to `http://localhost:8000`. To change it, set `VITE_API_URL` (for example, in `frontend/.env.local`). The backend's CORS settings allow `http://localhost:5173`.

## Layout

- `src/api.ts`: typed client for every backend route, with friendly error messages.
- `src/agents.ts`: each agent's label, role, icon, and color.
- `src/describe.ts`: turns audit records and tool results into plain sentences and honest ticket statuses.
- `src/components/`: `TicketBoard`, `Workspace` (roster, handoffs, timeline, outcome), `Decisions` (cash card and approval queue), `AgentAvatar`, and shared UI.
- `src/App.tsx`: page layout, polling, approval and reset dialogs, and notifications.

Design rationale: `output/design.md`.
