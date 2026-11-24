# Ayurvedic Herb Traceability Backend

Django REST Framework backend for herb collection, custody transfers, laboratory testing, manufacturing, finished products, QR verification, and a custom staff admin panel.

For the full project overview, workflows, model relationships, API reference,
setup details, and known limitations, see [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md).
The defensive security and business-logic review is in
[docs/SECURITY_AND_BUSINESS_GAPS.md](docs/SECURITY_AND_BUSINESS_GAPS.md).
The backend-to-Stitch screen and API gap analysis is in
[docs/STITCH_BACKEND_GAP_ANALYSIS.md](docs/STITCH_BACKEND_GAP_ANALYSIS.md).

## Setup

1. Create a virtual environment and install dependencies:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and configure Supabase PostgreSQL, a private Supabase Storage bucket, and email. The settings module loads `.env`. Set `SUPABASE_DATABASE_URL` and all `SUPABASE_STORAGE_*` values from your Supabase project; with them empty in development, Django uses local PostgreSQL (`POSTGRES_*`) or SQLite and local file storage. Keep `DJANGO_DEBUG=True` only for local development; production requires `DJANGO_DEBUG=False`, a strong random `DJANGO_SECRET_KEY` (50+ characters), explicit `DJANGO_ALLOWED_HOSTS`, and complete Supabase configuration.
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

## Deploy to Render

The root `render.yaml` defines a Render web service. Connect the repository to
Render and deploy the Blueprint. Render uses the checked-in `.python-version`
and `build.sh` to install dependencies, collect static files, and apply database
migrations during the build; the service runs Django with Gunicorn. The default
plan is Free and can spin down while idle. Select a paid plan in Render if the
service needs to stay available continuously.

Set the prompted secrets and configuration in the Render dashboard:

- `SUPABASE_DATABASE_URL` and `SUPABASE_DB_POOLER` from the Supabase database
  connection settings.
- All five `SUPABASE_STORAGE_*` values for the private Supabase Storage bucket.
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and
  `DEFAULT_FROM_EMAIL` for your SMTP provider. The deployed service uses SMTP,
  not the local console email backend.
- `CORS_ALLOWED_ORIGINS` with the exact origin(s) of the frontend, including
  `https://`. Keep `CORS_ALLOW_ALL_ORIGINS=False`.
- `CSRF_TRUSTED_ORIGINS` only when cross-origin browser POSTs or a custom
  domain require it; include the scheme, for example `https://...`.

Render generates `DJANGO_SECRET_KEY` and provides the service hostname. Django
uses that hostname for `ALLOWED_HOSTS`, HTTPS proxy detection, and the default
product-verification URL. Set `DJANGO_ALLOWED_HOSTS` or
`PRODUCT_VERIFICATION_BASE_URL` in the dashboard only when using custom domains.
Do not upload `.env` or paste its secrets into the Blueprint file.

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

The seed command is disabled unless `DJANGO_DEBUG=True`. The default password for
seeded normal users is `TestPass123`; change it when using local seed data. The
command does not overwrite an existing superuser. It creates
`seed.admin@example.com` only if no staff/superuser account exists.

## URLs

- Swagger: `http://localhost:8000/api/docs/`
- ReDoc: `http://localhost:8000/api/redoc/`
- OpenAPI schema: `http://localhost:8000/api/schema/`
- Custom admin panel app: `http://localhost:8000/panel/login/`
- Public product verification API: `/api/products/verify/<qr_reference>/`

## Authentication

Normal users register and verify email with OTP, then authenticate with JWT access and refresh tokens. Administrators authenticate with email and password through the custom session-based `/panel/` interface. Public administrator registration is disabled.

## File storage

When Supabase Storage is configured, uploads and generated QR images are stored
in the configured private bucket; otherwise development uses `upload/`. Private
organization documents and laboratory certificates are not exposed through a
public media URL; authenticated organization members, batch participants, and
staff can download them from the corresponding `/api/private/...` endpoints.
Active product images and QR images are streamed through the product asset
endpoint. Configuration and migration notes are in
[docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md#configure-supabase-postgresql).