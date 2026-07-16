# Digital Certificate Verification System

<<<<<<< HEAD
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
=======
A full-stack Digital Certificate Verification System built with FastAPI and PostgreSQL. The platform enables organizations to generate, manage, and verify digital certificates through a secure and scalable workflow.

The system allows administrators to upload certificate records in bulk via CSV files, automatically generates unique certificate IDs, QR codes, and PDF certificates, and provides a public verification interface for end users.

---

## Application Preview

### Verify Home

<img src="images/verify-home.png" width="900">

### Admin Dashboard

<img src="images/admin-home.png" width="900">

### Certificates Table

<img src="images/certificates-table.png" width="900">

---

## Features

- Bulk certificate generation via CSV uploads.
- Unique certificate ID generation.
- QR code generation for instant verification.
- PDF certificate generation using templates.
- Public certificate verification portal.
- Certificate download functionality.
- Certificate management dashboard.
- PostgreSQL-backed persistent storage.
- RESTful API built with FastAPI.
- Modular and scalable architecture.

---

## Tech Stack

| Component          | Technology            |
| ------------------ | --------------------- |
| Frontend           | HTML, CSS, JavaScript |
| Backend            | FastAPI               |
| Database           | PostgreSQL            |
| ORM                | SQLAlchemy            |
| Migrations         | Alembic               |
| PDF Generation     | ReportLab             |
| QR Code Generation | qrcode                |
| Validation         | Pydantic              |

---

## Project Structure

```text
certificate-verification/
│
├── app/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── config.py
│   ├── database.py
│   └── main.py
│
├── images/
│   ├── verify-home.png
│   ├── admin-home.png
│   └── certificates-table.png
│
├── static/
│   ├── certificates/
│   └── qr_codes/
│
├── uploads/
├── alembic/
├── requirements.txt
├── README.md
└── .env
>>>>>>> 546320c (Add project screenshots)
```

---

## API Endpoints

<<<<<<< HEAD
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
=======
| Method | Endpoint                                  | Description                          |
| ------ | ----------------------------------------- | ------------------------------------ |
| POST   | `/certificates/upload`                    | Upload CSV and generate certificates |
| GET    | `/verify/{certificate_id}`                | Verify a certificate                 |
| GET    | `/certificates`                           | Retrieve all certificates            |
| GET    | `/certificates/{certificate_id}`          | Retrieve certificate details         |
| GET    | `/certificates/{certificate_id}/download` | Download PDF certificate             |

---

## CSV Format

```csv
>>>>>>> 546320c (Add project screenshots)
recipient_name,recipient_email,certificate_title,issue_date,organization_name
John Doe,john@example.com,Python Programming,2026-07-13,Example Organization
Jane Doe,jane@example.com,Web Development,2026-07-13,Example Organization
```

---

## Certificate Generation Workflow

<<<<<<< HEAD
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
=======
1. Administrator uploads a CSV file.
2. The system validates all records.
3. Unique certificate IDs are generated.
4. Certificate data is stored in PostgreSQL.
5. QR codes are generated for each certificate.
6. PDF certificates are created.
7. Assets are stored in the server.
8. Certificates become publicly verifiable.

---

## Verification Workflow

```text
Scan QR Code
      ↓
Open Verification Page
      ↓
Retrieve Certificate
      ↓
Validate Certificate
      ↓
Display Result
```

---
>>>>>>> 546320c (Add project screenshots)

## Getting Started (Docker — recommended)

<<<<<<< HEAD
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

## Future Improvements

- Authentication and role-based access
- Bulk certificate download
- Email certificate delivery
- Cloud storage integration
- Certificate revocation management
- Multiple certificate templates

## License

This project is developed as part of the Digital Certificate Verification System for ECMA.
=======
### Clone the Repository

```bash
git clone <repository-url>
cd certificate-verification
```

### Create a Virtual Environment

```bash
python -m venv venv
```

#### Windows

```bash
venv\Scripts\activate
```

#### macOS/Linux

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/certificate_db
BASE_URL=http://localhost:8000
```

### Run Database Migrations

```bash
alembic upgrade head
```

### Start the Server

```bash
uvicorn app.main:app --reload
```

---

## Documentation

Once the application is running:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Future Improvements

- User authentication.
- Role-based access control.
- Email delivery of certificates.
- Bulk PDF downloads.
- Cloud storage integration.
- Certificate revocation support.
- Multiple certificate templates.
- Analytics dashboard.
- Docker deployment.

---

## License

Developed as part of the Digital Certificate Verification System project for Ethiopian Capital Market Authority.
>>>>>>> 546320c (Add project screenshots)
