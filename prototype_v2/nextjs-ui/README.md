# Optional Next.js UI

This folder is a small App Router reference client for the same FastAPI prototype.

```powershell
npm install
$env:NEXT_PUBLIC_API_BASE="http://127.0.0.1:8100"
npm run dev
```

Run the FastAPI prototype on port `8100` first. The Next.js app defaults to that API URL and uses the same order WebSocket endpoints.
