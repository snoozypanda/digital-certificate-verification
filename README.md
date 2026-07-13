# Digital Certificate Verification System Backend

A FastAPI backend for generating, storing, and verifying digital certificates. The system processes certificate data from CSV uploads, generates QR codes and PDF certificates, stores certificate records in PostgreSQL, and provides a public verification endpoint.

## Features

* Upload certificate data via CSV
* Automatically generate unique certificate IDs
* Generate QR codes for certificate verification
* Generate PDF certificates from a provided template
* Store certificate information in PostgreSQL
* Public certificate verification endpoint
* Download generated certificates
* Clean, modular FastAPI architecture

## Tech Stack

* **Framework:** FastAPI
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Database Migrations:** Alembic
* **QR Code Generation:** qrcode
* **PDF Generation:** ReportLab
* **Validation:** Pydantic

## Project Structure

```text
app/
├── models/
├── schemas/
├── services/
├── routers/
├── database.py
├── config.py
└── main.py

static/
├── certificates/
└── qr_codes/

uploads/
alembic/
```

## API Endpoints

| Method | Endpoint                                  | Description                                 |
| ------ | ----------------------------------------- | ------------------------------------------- |
| POST   | `/certificates/upload`                    | Upload a CSV file and generate certificates |
| GET    | `/verify/{certificate_id}`                | Verify a certificate                        |
| GET    | `/certificates`                           | List all certificates                       |
| GET    | `/certificates/{certificate_id}`          | Get certificate details                     |
| GET    | `/certificates/{certificate_id}/download` | Download the generated certificate PDF      |

## CSV Format

Example:

```csv
recipient_name,recipient_email,certificate_title,issue_date,organization_name
John Doe,john@example.com,Python Programming,2026-07-13,Example Organization
Jane Doe,jane@example.com,Web Development,2026-07-13,Example Organization
```

## Certificate Generation Workflow

1. Upload a CSV file.
2. Validate the uploaded data.
3. Generate a unique certificate ID for each recipient.
4. Store certificate information in PostgreSQL.
5. Generate a QR code containing the verification URL.
6. Generate a PDF certificate using the provided template.
7. Save generated assets.
8. Return the generation results.

## Verification Workflow

1. Scan the QR code.
2. Open the verification page.
3. Retrieve the certificate using its unique ID.
4. Display the certificate details and validation status.

## Getting Started

### Clone the repository

```bash
git clone <repository-url>
cd digital-certificate-backend
```

### Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**macOS/Linux**

```bash
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/certificate_db
BASE_URL=http://localhost:8000
```

### Run database migrations

```bash
alembic upgrade head
```

### Start the server

```bash
uvicorn app.main:app --reload
```

The API documentation will be available at:

* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`

## Future Improvements

* Authentication and role-based access
* Admin dashboard
* Bulk certificate download
* Email certificate delivery
* Cloud storage integration
* Certificate revocation management
* Multiple certificate templates

## License

This project is developed as part of the Digital Certificate Verification System.
