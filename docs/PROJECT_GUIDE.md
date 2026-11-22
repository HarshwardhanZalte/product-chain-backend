# Ayurvedic Herb Traceability Backend

This guide explains the backend as it is currently implemented: its actors,
business rules, workflows, data model, API routes, setup, and known limitations.
It is not a promise that every possible feature from a product specification is
implemented. The project is a Django/DRF backend; it does not include a separate
React, Vue, or mobile frontend.

## 1. Purpose and system boundary

The backend records the provenance and custody of herb batches through the
following chain:

```text
Account and organization onboarding
  -> farmer registers a herb batch
  -> batch is tested by a laboratory
  -> farmer/collector transfers custody to collector/factory
  -> factory records processing and input quantities
  -> factory allocates manufactured output to products
  -> product QR reference resolves to public traceability information
```

Supabase PostgreSQL is the system of record when configured.
Blockchain-related fields and
`BlockchainEvent` are placeholders only; the application does not submit
transactions or verify a blockchain. Public verification describes recorded
database state and is not an independent certification.

## 2. Technology and app ownership

- Python, Django 6.0.5, Django REST Framework 3.16.1
- JWT access and refresh tokens via Simple JWT
- OpenAPI, Swagger UI, and ReDoc via `drf-spectacular`
- Supabase PostgreSQL when `SUPABASE_DATABASE_URL` is set; local PostgreSQL or
  SQLite can be used for development
- Supabase Storage via its S3-compatible API when configured; local filesystem
  storage remains the development fallback
- Django admin plus a separate Django-template staff panel

| App | Owns |
|---|---|
| `users` | Custom email-based user, OTP records, activity logs, authentication, private file downloads, seed command |
| `organization` | Organizations and generic blockchain placeholders |
| `farmer` | Farmer profiles, herb batches, batch registration and history |
| `collector` | Collector profiles, transfer events and custody transition service |
| `lab` | Lab profiles, tests, results and certificates |
| `factory` | Factory profiles, manufacturing records and consumed batch inputs |
| `product` | Finished products, source batch links, QR generation and public verification |
| `admin_panel` | Custom staff-only session interface |
| `config` | Settings and top-level URL routing |

`/api/farmers/` and `/api/batches/` intentionally mount the same farmer URL
module. Use the former as the canonical prefix; the latter is a compatibility
alias, not a second implementation.

## 3. Actors, roles, and authorization

| Role | Main responsibilities |
|---|---|
| `FARMER` | Create an organization/profile, register batches, submit owned batches for lab testing, transfer batches to collectors |
| `COLLECTOR` | Create an organization/profile, receive transfers, submit owned batches for testing, transfer approved batches to factories |
| `LAB` | Create an organization/profile, receive tests, record results, approve or reject tests assigned to its lab profile |
| `FACTORY` | Create an organization/profile, accept addressed transfers, consume eligible input batches, create products and QR codes |
| `ADMIN` | Administrative role; public signup cannot create it. Staff/superuser privileges are used for administrative interfaces and actions. |

There are two important API permission levels:

1. **Verified active account:** the user is authenticated, active, and has a
   verified email. This is used for read access, profile onboarding, and some
   account operations.
2. **Approved business identity:** all of the above, plus an organization with
   `verification_status=VERIFIED` and the role-matching profile with
   `verification_status=VERIFIED`. This is required for core business writes.

Profile endpoints may create a missing profile on `GET`. Newly created profiles
default to `PENDING`; staff must approve the organization and role-matching
profile before the user can perform gated business operations. Profiles cannot
self-set their verification status through the profile serializer. The farmer
profile update explicitly checks for the farmer role; collector, lab, and
factory profile endpoints rely on authentication/email verification and do not
all independently reject a caller whose role differs from the profile route.
Treat these as self-profile setup endpoints, not role authorization.

Object scoping is endpoint-specific:

- Organization reads are limited to organization members and staff; organization
  updates require staff/admin permission.
- Farmers see their own batches; other authenticated business users see batches
  in their organization on farmer batch-list/detail routes.
- The collector available-batch endpoint currently returns all non-rejected,
  non-consumed batches when the caller has a collector profile; its queryset
  does not filter by organization or current owner. This is broader than
  organization-scoped visibility and should not be treated as a tenant-isolated
  inventory view.
- Transfers are visible to their sender or recipient.
- Lab tests are restricted to the assigned lab for lab operations.
- Manufacturing records and products are scoped to the user's factory profile,
  except staff list/detail access.
- Batch history is available to staff and users recorded as a batch participant
  (owner, farmer, transfer party, lab, manufacturing factory, or product
  manufacturer).
- Private organization documents and lab certificates require authentication
  and participant/member or staff access. Unauthorized private-file requests
  return not found.

## 4. Local setup and operations

Run commands in PowerShell from the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set Supabase database and S3 storage values in .env before running.
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`config/settings.py` loads the repository `.env`. A configured
`SUPABASE_DATABASE_URL` takes precedence over `POSTGRES_*`; if neither is
configured, the application uses `db.sqlite3`. A complete Supabase Storage
configuration selects remote storage; with all storage settings empty,
development uses local `upload/`. The default email backend is Django's console
backend, which prints email content to the runserver console. Configure SMTP
before relying on delivery outside local development.

### Main URLs

| URL | Purpose |
|---|---|
| `http://localhost:8000/admin/` | Built-in Django admin |
| `http://localhost:8000/panel/login/` | Custom staff panel |
| `http://localhost:8000/api/docs/` | Swagger UI |
| `http://localhost:8000/api/redoc/` | ReDoc |
| `http://localhost:8000/api/schema/` | OpenAPI schema |
| `/api/products/verify/<qr_reference>/` | Public product traceability response |
| `/api/private/organizations/<organization_id>/verification-document/` | Authenticated organization document download |
| `/api/private/lab-tests/<test_id>/certificate/` | Authenticated lab certificate download |

The Django admin and custom panel are separate interfaces. Both require staff
access; create a superuser with `python manage.py createsuperuser`.

### Environment variables

The names and local examples are in [.env.example](../.env.example).

| Group | Variables |
|---|---|
| Django runtime | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` |
| Supabase database | `SUPABASE_DATABASE_URL`, `SUPABASE_DB_POOLER`, `DB_CONN_MAX_AGE` |
| Local PostgreSQL fallback | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` |
| Supabase Storage | `SUPABASE_STORAGE_ENDPOINT`, `SUPABASE_STORAGE_REGION`, `SUPABASE_STORAGE_BUCKET`, `SUPABASE_STORAGE_ACCESS_KEY_ID`, `SUPABASE_STORAGE_SECRET_ACCESS_KEY` |
| Email | `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` |
| OTP | `OTP_EXPIRY_MINUTES`, `OTP_RESEND_COOLDOWN_SECONDS`, `OTP_MAX_ATTEMPTS` |
| JWT | `JWT_ACCESS_LIFETIME_MINUTES`, `JWT_REFRESH_LIFETIME_DAYS` |
| Media/QR | `MEDIA_URL`, `PRODUCT_VERIFICATION_BASE_URL` |
| Cross-origin API | `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_ALL_ORIGINS` |
| Throttling | `API_ANON_THROTTLE`, `API_USER_THROTTLE` |
| HTTPS deployment | `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD` |

With `DJANGO_DEBUG=False`, settings fail closed unless a strong
`DJANGO_SECRET_KEY` (at least 50 characters), explicit non-wildcard
`DJANGO_ALLOWED_HOSTS`, Supabase PostgreSQL URL, and complete Supabase Storage
configuration are provided. HTTPS redirect, secure cookies, and HSTS default
on in production mode. Only enable HSTS once every relevant host is HTTPS
capable; review proxy/SSL settings for your deployment.

`DEBUG` defaults to false if it is not set. The example `.env` is configured
for local development. Do not copy development credentials or the local test
database into production.

Configure explicit browser origins in `CORS_ALLOWED_ORIGINS`. The
`CORS_ALLOW_ALL_ORIGINS` flag is honored only in debug mode; wildcard origins
are rejected in production. In debug mode, a literal `*` inside
`CORS_ALLOWED_ORIGINS` is ignored—set the flag explicitly if unrestricted local
CORS is actually desired.

### Configure Supabase PostgreSQL

1. In Supabase, open **Project Settings → Database → Connection string** and
   copy a PostgreSQL URI for the desired connection type. Paste it into
   `SUPABASE_DATABASE_URL` in the local `.env`; do not commit or share the URI.
   The password must be URL-encoded if it contains reserved URI characters.
2. Set `SUPABASE_DB_POOLER=session` for a direct or session-pooler connection.
   Use `transaction` only with the transaction pooler; this config disables
   persistent connections and prepared statements for that mode.
3. Keep SSL enabled (`sslmode=require`). The application rejects a Supabase URI
   that explicitly disables SSL.
4. Run `python manage.py migrate` to create the Django application tables in
   the Supabase database.

Direct database connections may require IPv6 support in the runtime. If the
deployment host does not support it, use a Supabase session or transaction
pooler URI and configure the matching `SUPABASE_DB_POOLER` value. Django's
database URL overrides the existing `POSTGRES_*` development configuration.

### Configure Supabase Storage

1. Create a **private** bucket in Supabase Storage before starting the app.
   Use one bucket for organization documents, lab certificates, product images,
   and QR images, unless the deployment has a deliberate reason to separate
   them.
2. In **Storage → S3 configuration**, copy the exact endpoint and region. Set
   `SUPABASE_STORAGE_ENDPOINT` and `SUPABASE_STORAGE_REGION` from that page;
   do not guess/build the endpoint.
3. Generate an S3 Access Key ID and Secret Access Key in Supabase and set
   `SUPABASE_STORAGE_ACCESS_KEY_ID` and
   `SUPABASE_STORAGE_SECRET_ACCESS_KEY`. Set
   `SUPABASE_STORAGE_BUCKET` to the bucket name.
4. Restart the Django process. New uploads and QR images will be stored in
   Supabase; existing local files are not copied automatically.

The backend uses Django's S3-compatible storage integration with SigV4 and
non-overwriting object names. Keep the bucket private. S3 credentials have
privileged access and bypass Supabase Storage RLS, so they must only be
available to the server through environment secrets; never put them in the
browser or frontend. Product images and QR codes are streamed through the
existing application asset endpoint, and organization documents/certificates
are streamed through authenticated participant-only endpoints.

Official references: [Supabase PostgreSQL connections](https://supabase.com/docs/guides/database/connecting-to-postgres),
[Supabase S3 authentication](https://supabase.com/docs/guides/storage/s3/authentication),
and [Django-storages S3 backend](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html).

## 5. Business logic and end-to-end flows

### 5.1 Account registration, organization, and profile onboarding

1. A user registers with name, email, password, optional phone number, and one
   non-admin role.
2. Public registration cannot specify an organization or create an admin.
   The account is created with an unverified email.
3. The application creates and emails a random six-digit OTP. The verification
   and password-reset OTPs are separate by purpose. Resending applies a
   cooldown; verification applies expiry and a maximum number of attempts.
4. The user verifies email and can then log in for JWT tokens.
5. A verified user creates an organization through
   `POST /api/organizations/create/`. The organization type must match the
   user's role, it starts `PENDING`, and it is assigned to that user inside the
   same database transaction. A user already assigned to an organization
   cannot create another through this endpoint.
6. The user visits their role profile endpoint. If no profile exists, the
   endpoint creates one with `PENDING` verification status and sensible
   account-derived defaults; the user can then complete editable profile
   fields.
7. Staff review and approve organization/profile records. Until both are
   verified, core business writes are denied. Onboarding reads and profile
   completion remain possible before approval.

The role-to-organization type mapping is:

| User role | Organization type |
|---|---|
| `FARMER` | `FARMER_GROUP` |
| `COLLECTOR` | `COLLECTOR` |
| `LAB` | `TESTING_LAB` |
| `FACTORY` | `MANUFACTURER` |

`OTHER` is a model organization type but is not accepted by this self-service
onboarding mapping.

### 5.2 Batch registration and custody

1. An approved farmer submits herb, botanical name, amount, unit, source type,
   collection date/time, and origin details.
2. The server assigns a unique batch identifier, farmer profile, organization,
   current owner, initial `available_quantity` equal to `quantity`, and initial
   status `REGISTERED`. Client input cannot set ownership, available amount, or
   status.
3. The farmer may edit source information only while the batch is in
   `REGISTERED` or `COLLECTED`.
4. An approved current owner initiates a transfer. Allowed handoff roles are
   farmer to collector and collector to factory. The recipient must be an
   active, email-verified user with an approved organization and matching
   verified profile.
5. Until acceptance, the sender remains `current_owner`. The recipient accepts
   or rejects the pending event. Acceptance locks and rechecks the batch's
   owner, status, available amount, event recipient, and (for factory-bound
   transfers) latest approved lab test. Stale or invalid events are cancelled
   and do not change custody.
6. Acceptance sets current owner and status (`WITH_COLLECTOR` for collector;
   `SENT_TO_FACTORY` for factory). Rejection leaves custody with the sender.

**Whole-batch rule:** the transfer amount must equal all of
`available_quantity`. Partial transfer and batch splitting are not supported;
this avoids representing partial custody while the data model has only one
current owner.

The supported initiation/acceptance transitions are:

| Sender role | Batch status when initiated | Recipient role | Additional acceptance condition | Status after acceptance |
|---|---|---|---|---|
| Farmer | `REGISTERED`, `COLLECTED`, `APPROVED` | Collector | Current owner, quantity and recipient still match | `WITH_COLLECTOR` |
| Collector | `WITH_COLLECTOR`, `APPROVED` | Factory | Latest lab test is `APPROVED`; current owner, quantity and recipient still match | `SENT_TO_FACTORY` |

### Example request bodies

The following examples show the relationship between request IDs and the
workflow. Use actual IDs returned by earlier requests; user `to_party` is the
database primary key, while organization, lab, product, and manufacturing IDs
are UUID values.

Create a farmer-group organization after verifying email:

```json
{
  "organization_name": "Example Herb Cooperative",
  "organization_type": "FARMER_GROUP",
  "registration_number": "FARM-EXAMPLE-001",
  "email": "cooperative@example.com",
  "phone_number": "9000000000",
  "address": "Farm Road",
  "state": "Maharashtra",
  "district": "Pune",
  "pincode": "411001"
}
```

Register a batch after completing and obtaining approval for the farmer
profile and organization:

```json
{
  "herb_name": "Ashwagandha",
  "botanical_name": "Withania somnifera",
  "quantity": "10.000",
  "unit": "kg",
  "source_type": "CULTIVATED",
  "collection_date": "2026-11-20",
  "collection_time": "08:30:00",
  "collection_address": "Example Farm",
  "village": "Example Village",
  "district": "Pune",
  "state": "Maharashtra"
}
```

Initiate a farmer-to-collector transfer. `quantity` must equal the batch's
entire currently available amount:

```json
{
  "batch_id": "ASH-2026-00001",
  "to_party": 42,
  "quantity": "10.000",
  "transfer_location": "Collector depot",
  "remarks": "Harvest handoff"
}
```

Accept an incoming transfer as its addressed recipient:

```json
{
  "event_id": "00000000-0000-0000-0000-000000000001",
  "remarks": "Quantity and seals checked"
}
```

Submit an owned batch to an approved lab:

```json
{
  "batch_id": "ASH-2026-00001",
  "laboratory_id": "00000000-0000-0000-0000-000000000002",
  "test_type": "Purity and pesticide screening",
  "test_date": "2026-11-21",
  "test_parameters": {
    "purity_percent": 98.5,
    "pesticide_detected": false
  }
}
```

Record a result using `multipart/form-data` if attaching the certificate; the
other fields can be sent as JSON when no file is attached:

```json
{
  "test_id": "00000000-0000-0000-0000-000000000003",
  "test_result": "Passed",
  "result_summary": "Meets the laboratory's recorded parameters",
  "remarks": "Certificate filed"
}
```

Create a manufacturing record after the accepted transfer has put the batch in
`SENT_TO_FACTORY`:

```json
{
  "product_name": "Ashwagandha Powder",
  "process_date": "2026-11-21",
  "process_description": "Clean, dry, grind and sieve",
  "output_quantity": "8.000",
  "unit": "kg",
  "input_batches": [
    {
      "batch_id": "ASH-2026-00001",
      "quantity_used": "10.000"
    }
  ]
}
```

Create a product linked to the completed manufacturing record:

```json
{
  "manufacturing_id": "00000000-0000-0000-0000-000000000004",
  "product_name": "Ashwagandha Powder",
  "product_type": "Herbal powder",
  "manufacture_date": "2026-11-21",
  "batch_number": "ASH-POWDER-2026-001",
  "total_quantity": "8.000",
  "unit": "kg"
}
```

### 5.3 Laboratory testing

1. A verified batch owner submits an eligible owned batch to an approved lab
   profile. The batch moves to `SENT_TO_LAB`; a `PENDING` `LabTest` is assigned
   to that laboratory.
2. Only the assigned lab user can update the test. The test must still be
   active and the batch must still be owned by the original submitter and in
   the lab workflow.
3. The lab records results (and optionally parameters, summary, remarks, and
   a certificate). The certificate file is validated for extension, size, and
   file signature, then hashed with SHA-256. Recording results sets test and
   batch to `UNDER_TESTING`.
4. Approval requires an active `UNDER_TESTING` test with a non-empty result.
   Approval sets the test and batch to `APPROVED`. Rejection sets both to
   `REJECTED`.
5. A batch cannot be resubmitted for testing from `REJECTED`, `ON_HOLD`,
   `SENT_TO_FACTORY`, `IN_PROCESSING`, or `CONSUMED` status. A new test can be
   created for an owner-held batch in allowed states, including `APPROVED`;
   public verification uses the latest test, so a newer pending test makes the
   public result incomplete until it is resolved.

The certificate's existence is represented in public verification as a
boolean. Its contents are not served publicly; a permitted participant or
staff user downloads it through the private certificate endpoint.

### 5.4 Factory receipt and manufacturing

1. A collector initiates a transfer addressed to a factory. The factory uses
   `POST /api/factories/receive-batch/` with that pending transfer's `event_id`
   to accept it. This uses the same custody checks as collector acceptance.
2. Factory available-batch listing includes only batches currently owned by
   that factory, in `SENT_TO_FACTORY`, with positive available quantity.
3. Manufacturing accepts a product/process description, output amount/unit,
   and one or more `{batch_id, quantity_used}` inputs.
4. The server locks and validates each input: it must be factory-owned,
   `SENT_TO_FACTORY`, have enough available inventory, and have a unit equal to
   the manufacturing unit. Duplicate batch IDs are rejected.
5. One transaction creates the manufacturing record and input links,
   subtracts quantities, marks exhausted batches `CONSUMED`, and marks batches
   with remaining inventory `IN_PROCESSING`. The record is then marked
   `COMPLETED`.

**Current remainder limitation:** manufacturing eligibility and the factory's
available-batch list accept only `SENT_TO_FACTORY`, not `IN_PROCESSING`.
Consequently, a batch partially consumed in one manufacturing record retains a
positive quantity but cannot currently be selected for another record. Avoid
partial consumption until this lifecycle is extended, or treat the remainder
as an operational exception. The API also does not currently enforce
`output_quantity <= input_quantity`, conversion/yield rules, or product-date
semantics; the manufacturing output is an operator-entered recorded value.

### 5.5 Product allocation, QR, and public verification

1. A factory creates a product from one of its own completed manufacturing
   records. The record must have input links, the product unit must equal the
   record's output unit, and product quantity must be positive.
2. The manufacturing record is locked while total quantities of products
   already linked to it are summed. The new product cannot make total allocated
   product quantity exceed that record's `output_quantity`.
3. The product is linked to every manufacturing input herb batch. A random QR
   reference is assigned, and a PNG QR image points at
   `<PRODUCT_VERIFICATION_BASE_URL>/api/products/verify/<qr_reference>/`.
4. Public verification returns `REJECTED` if the product is on hold/rejected
   or an input batch/latest test is rejected. It returns `INCOMPLETE` if any
   batch lacks an approved latest test, is on hold, the product/manufacturing
   state is not complete/active, or there are no input links. It returns
   `VERIFIED` only when all input batches have an approved latest test and the
   product and manufacturing record are in their allowed states. Current edge
   case: when a rejected/held product has no input links, the final empty-input
   check changes the response status to `INCOMPLETE`.
5. Public output includes product name/type/batch number, manufacturer name,
   manufacturing details, herb origin, latest lab-test status, certificate
   availability, and recorded transfer history. A QR/image asset endpoint is
   public for active or completed products.

**Traceability allocation limitation:** every product created from one
manufacturing record receives links to all of that record's input batches with
the original manufacturing quantities. Product output is capped in aggregate,
but input quantities are not proportionally partitioned among multiple product
records. The links therefore establish provenance, not a material-balance
allocation for each individual product.

### 5.6 Password and administrator flows

- Forgot-password returns a generic response to avoid confirming whether an
  email exists. A delivery failure is logged; it does not expose account
  existence in the response.
- Reset-password requires the purpose-specific OTP and validates the new
  password. Change-password additionally requires the current password.
- Normal login returns JWT only for active, email-verified, non-admin users.
  Admin/staff users are directed to session-based administration.
- The custom panel authenticates staff users with email/password and Django
  sessions. The Django admin is available separately at `/admin/`.

## 6. OTP behavior and important authentication rules

The normal OTP is randomly generated, stored as a hash, expires after
`OTP_EXPIRY_MINUTES`, is limited by `OTP_MAX_ATTEMPTS`, and cannot be resent
until `OTP_RESEND_COOLDOWN_SECONDS` has elapsed. Verification and reset records
are scoped by both user and purpose.

The requested universal OTP is `098765`. It is accepted only when
`DJANGO_DEBUG=True`. With `DEBUG=False`, it does not bypass the ordinary OTP
checks; a valid active OTP record is mandatory. Debug mode must not be used with
real accounts or production data.

Password validators enforce configured Django password rules in registration,
reset, and change flows. JWT defaults are 30-minute access tokens and 7-day
refresh tokens; refresh rotation and blacklist-after-rotation are enabled.

## 7. API reference

All paths are relative to the application origin. Unless marked public, the
caller needs a Bearer access token. POST/PATCH bodies use JSON except file
uploads, which should use `multipart/form-data`. Swagger at `/api/docs/` shows
the generated schemas. List APIs are generally page-number paginated (20 rows
per page).

### Authentication — `/api/auth/`

| Method | Path | Body / behavior |
|---|---|---|
| POST | `/register/` | `name`, `email`, `password`, `role`; optional `phone_number`. No organization or admin role. |
| POST | `/send-otp/` | `email`; requests verification OTP, with generic response for unknown user |
| POST | `/resend-otp/` | `email`; refuses already verified account and applies cooldown |
| POST | `/verify-otp/` | `email`, `otp`; verifies email |
| POST | `/login/` | `email`, `password`; returns user and access/refresh tokens |
| POST | `/refresh/` | Simple JWT refresh-token request body |
| POST | `/logout/` | `refresh`; blacklists the refresh token |
| POST | `/forgot-password/` | `email`; requests password-reset OTP |
| POST | `/reset-password/` | `email`, `otp`, `new_password` |
| POST | `/change-password/` | Authenticated: `current_password`, `new_password` |
| GET | `/profile/` | Current authenticated user; email must be verified |

Full prefix: `/api/auth/`.

### Organizations — `/api/organizations/`

| Method | Path | Body / behavior |
|---|---|---|
| POST | `/create/` | Organization fields; type must match caller's role; starts `PENDING` and is assigned to caller |
| GET | `/list/` | Staff sees all; other users see their organization. Supports search/ordering. |
| GET | `/detail/<organization_id>/` | Member or staff read |
| PUT/PATCH | `/detail/<organization_id>/` | Staff/admin only |
| GET | `/my-organization/` | Current user's organization or 404 |

`verification_status`, timestamps, and organization ID cannot be assigned by
public API input. The verification document is write-only; download uses the
private endpoint listed below.

### Farmer and batches — `/api/farmers/` (also `/api/batches/`)

| Method | Path | Body / behavior |
|---|---|---|
| GET/PUT/PATCH | `/profile/` | Get or edit caller's farmer profile; GET may create a pending profile |
| GET | `/dashboard/` | Farmer batch counts |
| GET | `/batches/` | Scoped batch list; supports search/ordering |
| POST | `/batches/register/` | Herb, botanical name, positive quantity, unit, source, collection date/time and origin |
| GET | `/batches/detail/<batch_id>/` | Batch detail within caller's scope |
| PUT/PATCH | `/batches/detail/<batch_id>/` | Farmer may edit source fields only in `REGISTERED` or `COLLECTED` state |
| GET | `/batches/history/<batch_id>/` | Batch and chronological transfer, lab, manufacturing, product timeline for authorized participants |

The server controls batch ID, owner, farmer, organization, initial available
quantity, lifecycle status, and blockchain fields.

### Collector and custody — `/api/collectors/`

| Method | Path | Body / behavior |
|---|---|---|
| GET/PUT/PATCH | `/profile/` | Collector profile; GET may create a pending profile |
| GET | `/dashboard/` | Pending and accepted incoming transfer counts |
| GET | `/available-batches/` | Non-rejected/non-consumed batches if caller has a collector profile; current queryset is not organization- or owner-scoped |
| POST | `/transfer/initiate/` | `batch_id`, `to_party` (user DB ID), full `quantity`, `transfer_location`; optional `remarks` |
| GET | `/transfer/pending/` | Pending transfers addressed to caller |
| POST | `/transfer/accept/` | `event_id`, optional `remarks`; accepts addressed pending event |
| POST | `/transfer/reject/` | `event_id`, optional `remarks`; sender remains owner |
| GET | `/transfer/history/` | Events sent or received by caller |

Only farmer-to-collector and collector-to-factory role transitions are supported.
Custody changes only after recipient acceptance.

### Laboratory — `/api/labs/`

| Method | Path | Body / behavior |
|---|---|---|
| GET/PUT/PATCH | `/profile/` | Lab profile; GET may create a pending profile |
| GET | `/dashboard/` | Test counts by status |
| GET | `/requests/` | Tests assigned to caller's lab profile |
| POST | `/submit-batch/` | `batch_id`, `laboratory_id` (lab UUID), `test_type`, `test_date`; optional `test_parameters` |
| POST | `/submit-result/` | `test_id`; optional `test_parameters`, `test_result`, `result_summary`, `remarks`, `certificate_file` |
| POST | `/approve-test/` | `test_id`, optional `remarks`; requires an active test and recorded result |
| POST | `/reject-test/` | `test_id`, optional `remarks`; test must still be active |
| GET | `/test-history/` | Lab's tests; when caller has no lab profile, farmer's batch tests |

File uploads accept PDF/JPG/JPEG/PNG up to 10 MB and are checked against file
signatures. The API stores a SHA-256 certificate hash. The model also validates
the file; file content is not returned by the lab-test serializer.

### Factory and manufacturing — `/api/factories/`

| Method | Path | Body / behavior |
|---|---|---|
| GET/PUT/PATCH | `/profile/` | Factory profile; GET may create a pending profile |
| GET | `/dashboard/` | Manufacturing record counts |
| GET | `/available-batches/` | Factory-owned `SENT_TO_FACTORY` batches with positive quantity |
| POST | `/receive-batch/` | `event_id`, optional `remarks`; accepts a pending transfer addressed to factory |
| POST | `/manufacturing/create/` | `product_name`, `process_date`, `process_description`, `output_quantity`, `unit`, `input_batches: [{batch_id, quantity_used}]`; optional `remarks` |
| GET | `/manufacturing/list/` | Current factory's records (staff can see all) |
| GET | `/manufacturing/detail/<manufacturing_id>/` | Scoped manufacturing record detail |

Each input quantity must be positive and no greater than batch availability;
batch IDs must be unique within the request and all units must match the
manufacturing unit. The inventory update and record creation are atomic.

### Products — `/api/products/`

| Method | Path | Body / behavior |
|---|---|---|
| GET | `/list/` | Current factory's products; staff can see all |
| GET | `/detail/<product_id>/` | Scoped product detail |
| POST | `/create/` | `manufacturing_id`, `product_name`, `product_type`, `manufacture_date`, `batch_number`, positive `total_quantity`, `unit`; optional description, expiry, image |
| POST | `/qr/<product_id>/` | Regenerate QR for product owned by caller's factory; no body |
| GET, public | `/verify/<qr_reference>/` | Traceability response; unknown reference returns unavailable/404 |
| GET, public | `/<product_id>/assets/<asset>/` | Product image or QR asset for active/completed product; `asset` is `image` or `qr` |

The product's unit must match manufacturing output. Product quantities across
products linked to one manufacturing record may not exceed its output. Product
batch number and QR reference are unique.

### Private documents

| Method | Path | Access |
|---|---|---|
| GET | `/api/private/organizations/<organization_id>/verification-document/` | Organization members and staff |
| GET | `/api/private/lab-tests/<test_id>/certificate/` | Lab, batch, and transfer participants; staff |

Private documents are returned as attachments with `nosniff` and `no-store`
headers. Do not configure production web servers to expose the `upload/`
directory publicly.

## 8. Data model, relationships, and database rules

| Model | Purpose and important relationships |
|---|---|
| `User` | Unique email login, role, active/email-verified/staff flags, optional organization |
| `Organization` | Organization details, verification status, optional verification document |
| `FarmerProfile` | One-to-one user, belongs to organization, registers batches |
| `CollectorProfile` | One-to-one user and organization |
| `LabProfile` | One-to-one user and organization; owns assigned tests |
| `FactoryProfile` | One-to-one user and organization; owns manufacturing records/products |
| `HerbBatch` | Farmer, organization, current owner, amounts, origin, status, optional chain fields |
| `TransferEvent` | Batch, sender, recipient, their organizations, quantity, status and location |
| `LabTest` | Batch, assigned lab, submitting/reviewing users, results and optional certificate |
| `ManufacturingRecord` | Factory, creator, input/output quantities, process and status |
| `ManufacturingBatch` | Unique link per record/batch with quantity and unit consumed |
| `Product` | Factory, manufacturing record, product metadata, quantity and QR reference |
| `ProductBatch` | Unique product/source-batch link with quantity and unit |
| `EmailOTP` | User, OTP purpose, hash, expiry, attempts, resend time and consumed time |
| `ActivityLog` | Optional user, action, entity reference, description, IP and timestamp |
| `BlockchainEvent` | Generic text entity/event references; not a foreign-key relation |

Important database-level invariants:

- User email, organization registration number, herb batch ID, product batch
  number, product QR reference, and model UUID identifiers are unique.
- Transfer event quantity is greater than zero.
- Herb batch quantity and available quantity cannot be negative.
- Manufacturing input quantity is greater than zero; output quantity may be
  zero at the model constraint level.
- Manufacturing input link quantity, product quantity, and product-source link
  quantity must be greater than zero.
- A manufacturing record cannot link the same herb batch twice. A product
  cannot link the same herb batch twice.
- Critical transfer, manufacturing, and product-allocation writes use database
  transactions and row locks.

The database does not by itself enforce all business invariants. For example,
the API validates batch availability, role transitions, unit matching,
manufacturing-output allocation, and record ownership in service/view logic.

### Lifecycle/status values

| Entity | Status values |
|---|---|
| Organization | `PENDING`, `VERIFIED`, `REJECTED`, `SUSPENDED` |
| Role profiles | Farmer profile has `PENDING`, `VERIFIED`, `REJECTED`, `SUSPENDED`; collector/lab/factory store verification status and use the same operational values |
| Herb batch | `REGISTERED`, `COLLECTED`, `WITH_COLLECTOR`, `SENT_TO_LAB`, `UNDER_TESTING`, `APPROVED`, `REJECTED`, `ON_HOLD`, `SENT_TO_FACTORY`, `IN_PROCESSING`, `CONSUMED`, `COMPLETED` |
| Transfer | `INITIATED`, `ACCEPTED`, `REJECTED`, `CANCELLED` |
| Lab test | `PENDING`, `UNDER_TESTING`, `APPROVED`, `REJECTED`, `NEEDS_REVIEW` |
| Manufacturing | `PLANNED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` |
| Product | `DRAFT`, `ACTIVE`, `HOLD`, `REJECTED`, `COMPLETED` |

Not every status has an API transition. In particular, transitions such as
profile approval are administrative operations rather than public business
API actions.

## 9. Admin interfaces and seed data

### Django admin

The built-in admin is `/admin/`. It uses Django authentication and requires
`is_staff=True`; `createsuperuser` creates a staff, superuser, active, and
email-verified account with the `ADMIN` role.

### Custom staff panel

The template-based panel is mounted at `/panel/`, with login at
`/panel/login/`. It requires an active staff user and provides dashboard,
users, organizations, batches, lab tests, factories, products, and activity
views. It uses Django sessions, not JWT.

### Seed command

`python manage.py seed_test_data` creates deterministic local examples across
organizations, users/profiles, batches, transfers, lab tests, manufacturing,
products, OTP, blockchain placeholders, and logs. It accepts `--password` and
`--clear`. It is disabled unless `DJANGO_DEBUG=True`.

Seeded users use `TestPass123` by default; change it for local testing and never
expose a seeded database. The command creates a seed admin only if no
superuser exists. `--clear` removes selected seed records; it is not a general
database reset.

## 10. Known limitations and operational cautions

These are real scope limits of the current implementation, not features to
assume:

1. **No partial batch splitting.** Transfers require the entire available
   quantity.
2. **Partial manufacturing remainder is stranded.** A partially consumed
   batch becomes `IN_PROCESSING`, but subsequent manufacturing accepts only
   `SENT_TO_FACTORY`.
3. **Product input allocation is provenance, not mass balance.** Every product
   from one manufacturing record links to all the same inputs; there is no
   per-product proportional input allocation.
4. **No yield/conversion validation.** Manufacturing output is user-supplied;
   the API does not enforce output no greater than input or any drying/
   processing conversion rule.
5. **No independent certification or blockchain proof.** Public `VERIFIED`
   reflects stored records and latest lab state only.
6. **Public information is intentionally limited, but still public.** Public
   verification exposes origin and transfer location/date, manufacturer,
   product and test status, and certificate availability. Do not put
   confidential data in those fields.
7. **Some read operations have side effects.** Role profile `GET` may create a
   pending profile.
8. **Collector batch listing is not tenant scoped.** The current endpoint lists
   all batches except rejected/consumed when a collector profile exists. Review
   this behavior before exposing it to users across organizations.
9. **Some profile routes are permissive.** Collector/lab/factory profile
   endpoints do not all enforce that the authenticated user's role matches the
   profile route; verification status itself remains read-only. Keep these
   routes scoped to self-onboarding until role enforcement is made consistent.
10. **Admin review is important.** Verification status changes are not public
   self-service API operations; approve records through authorized staff/admin
   tooling.
11. **Email delivery is deployment dependent.** The console backend is for
   development. Production needs a working SMTP/provider configuration and
   operational monitoring.
12. **Supabase integration requires project secrets and a pre-created bucket.**
    The application does not create buckets or copy existing local uploads.
    Keep the configured bucket private, protect server-only S3 credentials, and
    arrange database and object-storage backups.

## 11. Verification and maintenance commands

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py spectacular --file schema.yaml --validate
```

`python manage.py check --deploy` evaluates production security settings. Run it
with production-like environment values; deployment checks should not be
interpreted using the local development `.env`.

## 12. API documentation and source of truth

The live OpenAPI schema is at `/api/schema/`; Swagger UI is `/api/docs/` and
ReDoc is `/api/redoc/`. Use the live schema for exact serializer fields,
required values, upload encodings, and paginated response shapes. Implementation
in views, serializers, permissions, and models remains authoritative when this
guide and runtime behavior differ.
