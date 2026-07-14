# Frontend for Digital Certificate Verification System

Two standalone pages, no build step required:

- **`verify.html`** — public certificate verification page. Anyone with a certificate ID or a QR code link can check validity.
- **`admin.html`** — staff dashboard to upload a recipient CSV, browse generated certificates, and download PDFs.

## How to run

Both files are plain HTML/JS (admin.html loads React from a CDN in the browser). Just open them directly in a browser, or serve them as static files:

```bash
python -m http.server 8080
# then visit http://localhost:8080/verify.html and http://localhost:8080/admin.html
```

Or serve them straight from the FastAPI backend by mounting a static folder in `app/main.py`:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
```

## Configuring the API URL

Both files auto-detect `localhost` and point to `http://localhost:8000`. In production, they default to `window.location.origin` (assumes the frontend and API share a domain). If your API lives on a different domain, edit the `API_BASE` constant near the top of each file's `<script>` block.

## CORS

If the frontend and backend are served from different origins, add CORS middleware to the FastAPI app so browsers allow the requests:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.org"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Assumptions I made about the API responses

The README didn't specify exact JSON response shapes, so I built against reasonable assumptions. Once your backend is live, check these against reality and adjust the JS if needed:

| Endpoint | Assumed response |
|---|---|
| `GET /verify/{id}` | `{ certificate_id, recipient_name, certificate_title, organization_name, issue_date, valid: true/false }` (or `status: "revoked"`) |
| `POST /certificates/upload` | `{ count: <number generated> }` plus a 2xx status on success |
| `GET /certificates` | Either a JSON array of certificate objects, or `{ items: [...] }` |
| `GET /certificates/{id}` | A single certificate object (not yet wired into the admin UI — currently the table links straight to download) |
| `GET /certificates/{id}/download` | Returns the PDF file directly, so it's used as a plain download link |

If the real field names differ (e.g. `full_name` instead of `recipient_name`), the fix is a find-and-replace in the relevant `<script>` block — the layout and styling won't need to change.

## What's not wired up yet

- A dedicated certificate detail view (`GET /certificates/{id}`) — currently the admin table only links to download; happy to add a detail modal once you confirm what fields that endpoint returns.
- Pagination for `/certificates` if the list grows large — right now it loads everything at once.
- Auth — the README lists this under "Future Improvements," so neither page currently expects a login step.
