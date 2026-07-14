# Digital Certificate Verification System

A full-stack system for generating, storing, and verifying digital certificates. The system processes certificate data from CSV/Excel uploads, generates QR codes and PDF certificates, stores certificate records in PostgreSQL, and provides a public verification page for recipients.

## Features

- Upload certificate data via CSV
- Automatically generate unique certificate IDs (format: `ECMA-2026-XXXXXX`)
- Generate QR codes for certificate verification
- Generate PDF certificates from a provided template
- Store certificate information in PostgreSQL
- Public certificate verification page (`verify.html`)
- Staff admin dashboard for uploads and management (`admin.html`)
- Download generated certificates
- Clean, modular FastAPI architecture
- Fully Dockerized — one command to run the whole stack

## Tech Stack

**Backend**
- Framework: FastAPI
- Database: PostgreSQL (via Docker)
- ORM: SQLAlchemy
- Database Migrations: Alembic
- QR Code Generation: `qrcode`
- PDF Generation: ReportLab
- Validation: Pydantic

**Frontend**
- `verify.html` — public certificate verification page
- `admin.html` — staff dashboard for uploading and managing certificates
- Plain `React.createElement` (no build step/JSX transpilation)
- Served locally via `python3 -m http.server 8080`

**Deployment**
- Docker Compose with two services: `api` (FastAPI) and `db` (PostgreSQL)

## Project Structure

```
app/
├── models/
├── schemas/
├── services/
├── routers/
├── database.py
├── config.py
└── main.py
frontend/
├── admin.html
├── verify.html
└── README.md
static/
├── certificates/
└── qr_codes/
uploads/
alembic/
docker-compose.yml
Dockerfile
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/certificates/upload` | Upload a CSV file and generate certificates |
| GET | `/certificates` | List all certificates |
| GET | `/certificates/{certificate_id}` | Get certificate details |
| GET | `/certificates/{certificate_id}/download` | Download the generated certificate PDF |
| GET | `/verify/{certificate_id}` | Verify a certificate (public) |
| GET | `/health` | Health check |

## CSV Format

Example:
```
recipient_name,recipient_email,certificate_title,issue_date,organization_name
John Doe,john@example.com,Python Programming,2026-07-13,Example Organization
Jane Doe,jane@example.com,Web Development,2026-07-13,Example Organization
```

## Certificate Generation Workflow

1. Upload a CSV file via `admin.html` or `/certificates/upload`.
2. Data is validated.
3. A unique certificate ID is generated for each recipient (`ECMA-2026-XXXXXX`).
4. Certificate information is stored in PostgreSQL.
5. A QR code containing the verification URL is generated.
6. A PDF certificate is generated using the provided template.
7. Generated assets are saved to `static/certificates/` and `static/qr_codes/`.
8. Results are returned to the admin dashboard.

## Verification Workflow

1. Recipient scans the QR code or visits the verification page directly.
2. `verify.html` calls `/verify/{certificate_id}`.
3. Certificate details and validation status (`VALID`/`REVOKED`/`NOT FOUND`) are displayed.

## Getting Started (Docker — recommended)

1. **Clone the repository**
   ```
   git clone <repository-url>
   cd certificate-verification
   ```

2. **Set up environment variables**
   Copy `.env.example` to `.env` and fill in real values:
   ```
   cp .env.example .env
   ```

3. **Start the backend stack**
   ```
   docker compose up -d
   ```
   This builds and runs both the `api` (FastAPI) and `db` (PostgreSQL) containers. Migrations run automatically on startup.

4. **Confirm the API is healthy**
   ```
   curl http://localhost:8000/health
   ```

5. **Serve the frontend**
   ```
   cd frontend
   python3 -m http.server 8080
   ```
   Then open:
   - Verification page: `http://localhost:8080/verify.html`
   - Admin dashboard: `http://localhost:8080/admin.html`

6. **API documentation**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

### Rebuilding after code changes

If you change backend code or the Dockerfile:
```
docker compose build --no-cache api
docker compose up -d
```

## Notes for Contributors

- Changes to shared backend files (especially `app/main.py`) should go through a GitHub Issue first so collaborators can weigh in before merging.
- CORS is currently open (`allow_origins=["*"]`) for local development. **This must be locked down to the real production domain(s) before launch** — see open issues.
- Frontend uses plain `React.createElement` deliberately — Babel/JSX in-browser transpilation caused rendering issues in this setup.

## Future Improvements

- Authentication and role-based access
- Bulk certificate download
- Email certificate delivery
- Cloud storage integration
- Certificate revocation management
- Multiple certificate templates

## License

This project is developed as part of the Digital Certificate Verification System for ECMA.
