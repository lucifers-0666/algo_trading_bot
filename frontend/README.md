# React frontend

A light-first React + TypeScript dashboard shell for the Indian AI paper-trading platform.

## Stack

- React 19.3
- Vite 8
- TypeScript
- TanStack Query for server-state caching
- Lucide icons
- CSS design tokens (no large component framework)

## Requirements

Node.js >= 22.12.0 and npm.

## Run

From this directory:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

The development server binds to `127.0.0.1:5173` and proxies `/api` to `127.0.0.1:8000`.

Build and type-check:

```powershell
npm run typecheck
npm run build
```

## Data safety

The dashboard never manufactures market quotes. In the absence of a working API/provider connection, values are shown as unavailable. All displayed capital is configured virtual capital. Never put provider credentials in `VITE_*` variables: Vite exposes them to browser code.

The backend is the authoritative source for P&L, indicators, risk checks and simulated order state.
