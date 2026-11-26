# Stitch UI to Backend Gap Analysis

**Review date:** 2026-11-25
**Design source:** [Product Chain Traceability Dashboard in Google Stitch](https://stitch.google.com/projects/3137115857976930985)  
**Scope:** Backend routes, model/schema fields, serializers and response contracts, permissions, workflow behavior, and existing tests. Frontend source code and frontend implementation were not reviewed.

## Executive summary

The Stitch project describes 37 screens across authentication/onboarding,
Farmer, Collector, Lab, Factory, and public consumer verification. The backend
now supports the main matching onboarding, participant discovery, harvest
evidence, custody, laboratory measurement, manufacturing draft, product
lineage, and public verification flows.

The backend gaps that blocked those flows have been implemented and tested.
The remaining differences are deliberate limits or follow-up product choices:
there are no partial-batch transfers, EXIF/HEIC/MP4 processing, sensor or
equipment telemetry, external certification integrations, or real blockchain
transactions. The UI must not display invented values for those features.

## Stitch screen inventory

The Stitch project lists the following 37 screens:

| Portal | Screens | Backend coverage at a glance |
|---|---:|---|
| Authentication and onboarding | 10 | Registration, OTP, role onboarding status, and staff review are available |
| Farmer | 9 | Batch metadata, validated field evidence uploads, and batch history are available |
| Collector | 6 | Owned-batch visibility, verified participant discovery, and whole-batch transfer flows are available |
| Quality Testing Lab | 4 | Verified Lab discovery, structured measurements, test detail, search, and ordering are available |
| Factory / Processing | 6 | Typed process fields, manufacturing drafts, input lineage, product lineage, and QR are available |
| Public Consumer Verification | 2 | Public product/source details, approved assay measurements, and product asset URLs are available; QR scanning remains client-side |

The staff administration interface is not part of this 37-screen inventory.
The backend has a session-based staff panel at `/panel/` and Django Admin at
`/admin/`; it does not expose a general staff REST API.

## What is already present

### Persisted data and relationships

The current schema contains:

- Custom email-based `User`, OTP, and activity-log records.
- `Organization` and Farmer, Collector, Lab, and Factory profiles.
- `HerbBatch` with botanical names, quantity/unit, source type, collection
  date/time, coordinates, origin address, owner, organization, and lifecycle
  status.
- `TransferEvent` for sender, recipient, organizations, quantity, location,
  status, and timestamps.
- `LabTest` with free-form JSON parameters, text result/summary, certificate
  file/hash, status, and reviewer.
- Manufacturing records and input-batch links.
- Products and product-to-input-batch links, image, QR reference, and status.
- Generic blockchain-event placeholders; these do not perform or prove
  blockchain transactions.

The model files are [users/models.py](../users/models.py),
[organization/models.py](../organization/models.py),
[farmer/models.py](../farmer/models.py),
[collector/models.py](../collector/models.py),
[lab/models.py](../lab/models.py), [factory/models.py](../factory/models.py),
and [product/models.py](../product/models.py).

### Existing workflow routes

| Workflow | Available backend routes |
|---|---|
| Register, verify OTP, resend OTP, login, refresh/logout tokens, password reset/change, user profile, onboarding summary | `/api/auth/` |
| Create/read organization, current organization, verified participant directory (`role` and optional `search`) | `/api/organizations/` |
| Farmer profile, dashboard, batch create/list/detail/history, batch field-evidence upload/list | `/api/farmers/` (also mounted at `/api/batches/`) |
| Collector profile, dashboard, owned available batches, initiate/accept/reject transfers, transfer history | `/api/collectors/` |
| Lab profile, dashboard, requests (search/order), test detail, submit test/result, approve/reject, history | `/api/labs/` |
| Factory profile/dashboard, available batches, receive transfer, create/complete/cancel/list/read manufacturing records | `/api/factories/` |
| Product create/list/detail, regenerate QR, public assets, enriched public verification | `/api/products/` |
| Private organization verification document and lab certificate downloads | `/api/private/...` |

Role-based business writes require a verified active account, a verified
organization, and a verified role profile. Organization/profile review is not
self-service.

## Screen-to-backend assessment

### 1. Authentication and onboarding

**Present**

- `POST /api/auth/register/`, `verify-otp/`, `resend-otp/`, `login/`,
  `refresh/`, `logout/`, `forgot-password/`, `reset-password/`, and
  `change-password/`.
- `POST /api/organizations/create/` accepts organization fields and an
  optional verification document. The organization is assigned to the caller
  and starts in `PENDING`.
- `GET /api/organizations/my-organization/` returns organization status.
- Role profile endpoints (`/api/farmers/profile/`, `/api/collectors/profile/`,
  `/api/labs/profile/`, `/api/factories/profile/`) expose profile fields and
  verification status. A profile GET can create a pending profile.
- Both `/admin/` and the session-based `/panel/` are separate from normal
  user JWT login.

**Gaps**

- `GET /api/auth/onboarding/` aggregates the caller's organization, role
  profile, verification state, and next step. A user's profile may still be
  absent until the profile endpoint creates it.
- The custom staff panel changes organization verification status, but does
  not provide role-profile approval actions. Profile statuses are editable in
  Django Admin; if staff review is meant to happen only in `/panel/`, add
  review actions there or add a carefully permissioned staff API.
- Registration and login OpenAPI response schemas now match their actual
  response bodies.
- The debug-only universal OTP is `098765`; it is accepted only while
  `DEBUG=True`. Normal random OTPs remain supported.

### 2. Farmer portal

**Present**

- Dashboard: `GET /api/farmers/dashboard/`.
- Batches: list, register, detail/edit, and history endpoints.
- Transfer initiation: `POST /api/collectors/transfer/initiate/`.
- Core persisted batch fields include herb and botanical names, description,
  quantity/unit, cultivated/wild-collected source, collection date/time,
  coordinates, collection address, village/district/state, and remarks.

**Gaps against the batch-entry and traceability designs**

- `HerbBatch` now persists plant part, cultivar, quality grade, packaging
  details, drying notes, and the GACP attestation flag.
- `POST` and `GET /api/farmers/batches/detail/<batch_id>/evidence/` provide
  one-file-at-a-time evidence upload and participant-scoped listing. The
  original Farmer can upload only before transfer; each batch is limited to
  eight files. Uploads use existing file validation and valid-image checks.
- EXIF extraction/verification, HEIC and video uploads, and draft batch
  registration remain unsupported. The shared validator's file-size/type
  limits still apply.
- No draft batch state or save-draft operation exists. Registration creates a
  `REGISTERED` batch.
- Registering a batch does not automatically create a Lab request. Lab
  submission is a separate action that requires the caller to choose a
  laboratory.
- The dashboard response only contains `total_batches`, `registered`,
  `approved`, and `rejected`. Recent batches, total available quantity,
  testing progress, and recent custody activity must be fetched separately or
  are unavailable.
- Batch detail returns the `HerbBatch` serializer; the separate history route
  provides the compact timeline. The evidence route is separate as well.
- The UI displays a local harvest timestamp; the model stores separate
  `DateField` and `TimeField` values without timezone/offset provenance.

### 3. Collector portal

**Present**

- Dashboard counts pending and accepted incoming transfers.
- Pending transfers, accept/reject actions, transfer history, and batch
  availability are exposed through `/api/collectors/`.
- A Collector can initiate a full-batch transfer to a Factory.

**Gaps and blockers**

- `GET /api/organizations/participants/?role=COLLECTOR|FACTORY|LAB&search=...`
  returns paginated, active, email-verified users with verified organizations
  and role profiles. It includes both the numeric user `id` expected by the
  transfer request and UUID/profile/organization identifiers for client use.
- `GET /api/collectors/available-batches/` is scoped to the authenticated
  Collector's owned inventory with positive quantity and eligible status.
- The transfer design exposes editable quantity, but transfer logic rejects
  anything other than the full available batch quantity. Either make the
  client contract explicitly whole-batch or design a real split-lot/custody
  model; changing only the quantity check would break ownership and
  traceability invariants.
- Transfer records do not store carrier/vehicle, IoT sensor, route,
  temperature/humidity telemetry, seal, handover PIN/signature, or a generated
  receipt. These must not be rendered as real backend data.
- Transfer responses now add the human-facing batch ID, herb names, unit,
  party names, and organization labels alongside the original model fields.
- There is no transfer detail route; pending/history lists can be used as
  sources, but the client must handle their page shape and retrieve batch
  detail separately.

### 4. Quality Testing Lab portal

**Present**

- Dashboard counts tests by pending, under-testing, approved, and rejected.
- Lab requests/history lists, sample submission, result submission, approval,
  rejection, and private certificate download exist.
- `LabTest` has flexible `test_parameters` JSON, result/summary/remarks,
  certificate file and hash, status, and reviewer.

**Gaps and blockers**

- The participant directory supplies eligible Labs and their profile and
  organization identifiers.
- Assay measurements are stored as structured rows with analyte, method,
  result, optional numeric value/unit/threshold, and verdict. Tests can be
  retrieved at `GET /api/labs/tests/<test_id>/`; request lists support
  search/order filters.
- Measurement data does not include instrument calibration, signed assessor,
  or third-party LIMS/NABL verification. Lab certificate files remain private.
- Sample custody intake, courier/seal records, chain-of-custody checklist,
  equipment telemetry, and external LIMS/NABL synchronization are not
  modeled or implemented.
- The certificate endpoint is private to authorized participants and staff.
  Public verification only states whether a certificate exists; it does not
  provide a public certificate URL. Decide the intended public disclosure
  policy rather than making private documents public by assumption.

### 5. Factory / Processing portal

**Present**

- Factory dashboard, available input batches, incoming receipt, manufacturing
  creation/list/detail, products list/create/detail, and QR regeneration.
- Manufacturing atomically creates the record, links input batches, and
  decrements batch availability.
- Product creation checks that the manufacturing record is completed, units
  match, and total product allocation does not exceed output.
- Product images and QR images are served through application asset routes.

**Gaps against the operations and product screens**

- `ManufacturingRecord` now also stores facility line, shift, SOP reference,
  solvent/method, target yield, typed JSON process parameters, and QC lead.
  Hardware telemetry is not generated or inferred.
- `save_as_draft` creates a planned record without consuming inventory;
  `/manufacturing/complete/` re-locks and revalidates the input batches before
  consumption, and `/manufacturing/cancel/` cancels a planned draft.
- Manufacturing responses now include nested input-batch identifiers,
  quantities, units, and available quantities.
- Product metadata such as expiry is supported by the separate product
  endpoint, not the manufacturing endpoint. The workflow is two-step:
  create manufacturing record, then create one or more Products.
- Product list/detail responses now include source-batch lineage and nested
  manufacturing data.
- Current product links copy every manufacturing input link onto each product.
  They do not calculate the actual input amount attributable to each product.
  Do not treat those amounts as per-product mass balance.
- Batch-print QR labels and production-log exports are not API endpoints.
  Product QR data can be obtained from the product serializer/asset route;
  print layout/export generation would need another backend operation only if
  the server must generate it.
- The dashboard only returns counts (`manufacturing_records`, `completed`,
  `in_progress`). Active vats, line telemetry, and recent activity are not
  backed by an API.

### 6. Public consumer verification

**Present**

- `GET /api/products/verify/<qr_reference>/` returns public verification
  status, product/manufacturer summary, manufacturing summary, source batch
  origin, latest test status, certificate-availability flag, and transfer
  locations/dates.
- `GET /api/products/<product_id>/assets/<asset>/` serves active/completed
  product image or QR image.
- QR references and product batch numbers are unique.

**Gaps**

- QR camera scanning is not a backend operation. The backend supports lookup
  once the frontend has extracted a QR reference/URL.
- Public verification returns assay measurements only for an approved latest
  test and includes product UUID, image URL, and QR URL when present.
- Certificate content/URLs, GPS coordinates, rich custody actors/signatures,
  and blockchain proof remain intentionally excluded from public output.
- Define a privacy-reviewed public response schema before exposing more
  farmer, location, organization, lab, or certificate information.

## API response contract notes

The following response shapes are confirmed from the current views and
serializers; they should be treated as the integration contract until explicit
response serializers are added.

| Endpoint | Current shape / limitation |
|---|---|
| `POST /api/auth/login/` | `{"user": UserSerializer, "tokens": {"access": "...", "refresh": "..."}}` |
| `POST /api/auth/register/` | `{"detail": "Registration successful. Verify your email with the OTP."}`; documented as `DetailResponseSerializer` |
| `GET /api/auth/onboarding/` | Aggregate current user, organization/profile state, and suggested next step |
| Role dashboards | Role-specific flat count objects; not a common dashboard schema |
| List endpoints | Page-number pagination, default page size 20; many list endpoints have no search/order filters |
| Participant directory | Paginated role-filtered records include numeric user `id`, UUID, profile, and organization display fields |
| Transfer list/action | `TransferEventSerializer` retains model fields and adds readable batch, party, organization, and unit values |
| Lab test list/action | `LabTestSerializer` includes structured measurements; certificate file is write-only and `certificate_available` is supplied |
| Manufacturing create/detail | `ManufacturingRecordSerializer` includes nested input-batch data; draft creation does not reserve stock |
| Product list/create/detail | `ProductSerializer` includes source-batch lineage and manufacturing summary |
| Batch history | `{"batch": HerbBatchSerializer, "history": [...]}`; event entries vary by `event_type` and are not represented by a single declared event schema |
| Public verify | `verification_status`, `product` and asset URLs, `manufacturing`, `input_herb_batches`, and measurements for approved latest tests; certificate content remains private |
| Factory receive | Returns `{"detail": "Batch received by factory.", "batch_id": "..."}`; OpenAPI currently documents `ReceiveBatchSerializer` as the response |

Several `@extend_schema` declarations still use generic `OpenApiTypes.OBJECT`
or `responses={200: None}` for meaningful JSON bodies. OpenAPI generation
validates without errors, but explicit response serializers for all remaining
endpoints would improve client generation. Three enum-name collision warnings
remain in schema generation.

## Remaining work and intentional limits

The previously identified P0 integration blockers are addressed: Collector
inventory is owner-scoped; verified participant discovery is available;
transfer, lab, manufacturing, product, and onboarding responses now include
the data needed by their corresponding screens; and structured harvest,
evidence, assay, and manufacturing inputs are persisted.

The following items remain product decisions or separate integrations, not
implemented behavior:

1. **Partial-batch transfers.** Transfers remain whole-available-quantity
   operations. Supporting the quantity selector as a true partial transfer
   requires a split-lot model and custody/mass-balance rules; do not remove the
   server-side constraint without that design.
2. **Farmer batch drafts.** Batch registration creates a `REGISTERED` record;
   a save-draft workflow is not implemented.
3. **Evidence media processing.** Uploads support one validated file per
   request, up to eight files per batch, using the existing document/image
   validators. EXIF verification, HEIC, and video uploads are not supported.
4. **Telemetry and external verification.** No sensor readings, equipment
   telemetry, calibration data, external lab/certification checks, signed
   assessor attestations, or LIMS/NABL synchronization are supplied.
5. **Blockchain.** Existing fields/events are placeholders only; there are no
   real transactions, signatures, proofs, or generated hashes.
6. **Quantitative product lineage.** Product source links inherit each
   manufacturing input link; they are provenance references, not per-product
   ingredient allocations or mass-balance measurements.
7. **Administration and dashboard breadth.** Profile review actions in the
   custom `/panel/` and richer dashboard aggregates/recent-activity feeds are
   not included in this change.
8. **OpenAPI consistency.** Schema validation has zero errors, but some
   endpoints still use generic response schemas, and three enum-name
   collision warnings remain.
9. **Public disclosure.** Public verification exposes approved assay rows and
   limited source geography. Certificates, GPS coordinates, named custody
   actors, signatures, and private documents remain excluded.

## Verification performed

- Added migrations for Farmer harvest/evidence fields, structured Lab
  measurements, and Factory manufacturing process fields.
- Full suite: **42 tests passed** using an explicitly configured in-memory
  SQLite database and in-memory email backend. The test run did not connect
  to Supabase.
- `manage.py check`: passed.
- `makemigrations --check --dry-run`: no model/migration drift detected.
- OpenAPI generation/validation: **0 errors**, with three enum naming
  collision warnings.
- `git diff --check`: passed.
- Migrations have **not** been applied to Supabase.
- No frontend files were read, tested, or changed.

For current route and business-flow details, see
[PROJECT_GUIDE.md](PROJECT_GUIDE.md). The runtime OpenAPI schema and
[config/urls.py](../config/urls.py) remain authoritative for the actual API
surface.
