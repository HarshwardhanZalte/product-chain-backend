# Ayurvedic Herb Traceability Backend

Django REST Framework backend for herb collection, custody transfers, laboratory testing, manufacturing, finished products, QR verification, and a custom staff admin panel.

## Setup

1. Create a virtual environment and install dependencies:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and configure PostgreSQL and email settings. A PostgreSQL environment enables PostgreSQL; without `POSTGRES_DB`, Django uses SQLite for local development.
3. Apply migrations:
   ```powershell
   python manage.py migrate
   ```
4. Create an administrator:
   ```powershell
   python manage.py createsuperuser
   ```
5. Run the server:
   ```powershell
   python manage.py runserver
   ```

## Test data

Create repeatable test data for users, organizations, profiles, batches, transfers,
laboratory tests, manufacturing records, products, OTP records, activity logs, and
blockchain placeholders:

```powershell
python manage.py seed_test_data
```

Reset and recreate the seed records:

```powershell
python manage.py seed_test_data --clear
```

The default password for seeded normal users is `TestPass123`. The command does not
overwrite an existing superuser. It creates `seed.admin@example.com` only if no
staff/superuser account exists.

## URLs

- Swagger: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- OpenAPI schema: `http://localhost:8000/api/schema/`
- Custom admin panel app: `http://localhost:8000/panel/login/`
- Public product verification: `/api/product/verify/<qr_reference>/`

## Authentication

Normal users register and verify email with OTP, then authenticate with JWT access and refresh tokens. Administrators authenticate with email and password through the custom session-based `/panel/` interface. Public administrator registration is disabled.

## File storage

Uploads are stored below `upload/` in development and served by Django when `DJANGO_DEBUG=True`. Private certificates and organization documents require a production private-media server or signed application endpoint; they should not be placed behind public static serving.
