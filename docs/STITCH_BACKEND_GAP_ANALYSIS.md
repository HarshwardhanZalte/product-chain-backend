# Stitch UI to Backend Gap Analysis

**Review date:** 2026-11-24  
**Design source:** [Product Chain Traceability Dashboard in Google Stitch](https://stitch.google.com/projects/3137115857976930985)  
**Scope:** Backend routes, model/schema fields, serializers and response contracts, permissions, workflow behavior, and existing tests. Frontend source code and frontend implementation were not reviewed.

## Executive summary

The Stitch project describes 37 screens across authentication/onboarding,
Farmer, Collector, Lab, Factory, and public consumer verification. The backend
already supports the main account, organization, batch, custody, testing,
manufacturing, product, QR, and public verification workflows.

It is **not yet a complete backend contract for the designs**. Important
screen flows cannot reliably populate their choices or details; several
prominent fields are not represented in the database; some list/detail
responses expose only related database keys; and the ledger, sensor, and
laboratory measurement content shown in the designs is not backed by equivalent
structured data. Some such UI can be implemented with real supported data,
but it must not present generated blockchain proofs, sensor readings,
certification, or assay measurements as if this backend had verified them.

## Stitch screen inventory

The Stitch project lists the following 37 screens:

| Portal | Screens | Backend coverage at a glance |
|---|---:|---|
| Authentication and onboarding | 10 | Mostly covered; application status requires multiple calls and staff review |
| Farmer | 9 | Core batch and transfer routes exist; harvest evidence and rich batch metadata are missing |
| Collector | 6 | Core incoming/outgoing transfer routes exist; recipient discovery and transport telemetry are missing |
| Quality Testing Lab | 4 | Request/result/status routes exist; structured assays and lab discovery are missing |
| Factory / Processing | 6 | Manufacturing, products, and QR routes exist; process telemetry and several form fields are missing |
| Public Consumer Verification | 2 | Public lookup and QR asset routes exist; camera scanning is a client feature and the response is less detailed than the design |

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
| Register, verify OTP, resend OTP, login, refresh/logout tokens, password reset/change, user profile | `/api/auth/` |
| Create/read organization, current organization | `/api/organizations/` |
| Farmer profile, dashboard, batch create/list/detail/history | `/api/farmers/` (also mounted at `/api/batches/`) |
| Collector profile, dashboard, available batches, initiate/accept/reject transfers, transfer history | `/api/collectors/` |
| Lab profile, dashboard, requests, submit test, record result, approve/reject, history | `/api/labs/` |
| Factory profile/dashboard, available batches, receive transfer, create/list/read manufacturing records | `/api/factories/` |
| Product create/list/detail, regenerate QR, public assets, public verification | `/api/products/` |
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

- There is no single onboarding/status endpoint. A client must combine the
  current user, organization, and role-profile calls and handle cases where an
  organization or profile does not exist yet.
- The custom staff panel changes organization verification status, but does
  not provide role-profile approval actions. Profile statuses are editable in
  Django Admin; if staff review is meant to happen only in `/panel/`, add
  review actions there or add a carefully permissioned staff API.
- The registration endpoint is documented as returning `UserSerializer`, but
  its actual response contains a `detail` message. Correct the OpenAPI response
  schema.
- The debug universal OTP is `666666` in
  [users/services.py](../users/services.py), while existing tests submit
  `098765`. Both debug universal-OTP tests currently fail. Resolve this
  backend behavior before relying on the OTP flow in development; the
  universal value is debug-only.

### 2. Farmer portal

**Present**

- Dashboard: `GET /api/farmers/dashboard/`.
- Batches: list, register, detail/edit, and history endpoints.
- Transfer initiation: `POST /api/collectors/transfer/initiate/`.
- Core persisted batch fields include herb and botanical names, description,
  quantity/unit, cultivated/wild-collected source, collection date/time,
  coordinates, collection address, village/district/state, and remarks.

**Gaps against the batch-entry and traceability designs**

- The registration form shows plant tissue/part, cultivar/variety, quality
  grade, packaging configuration, field/cultivation/drying observations,
  attestations, and field photo/video evidence with EXIF verification. These
  are not persisted by `HerbBatch`; there is no field-evidence model or
  upload endpoint for them.
- `description` and `remarks` are generic text fields, not validated,
  independently queryable values for those form sections.
- No draft batch state or save-draft operation exists. Registration creates a
  `REGISTERED` batch.
- Registering a batch does not automatically create a Lab request. Lab
  submission is a separate action that requires the caller to choose a
  laboratory.
- The dashboard response only contains `total_batches`, `registered`,
  `approved`, and `rejected`. Recent batches, total available quantity,
  testing progress, and recent custody activity must be fetched separately or
  are unavailable.
- Batch detail returns the `HerbBatch` serializer, not a joined traceability
  view. History is available separately and contains a compact event timeline;
  lab measurements, certificate metadata, and manufacturing inputs are not
  consolidated into that response.
- The UI displays a local harvest timestamp; the model stores separate
  `DateField` and `TimeField` values without timezone/offset provenance.

### 3. Collector portal

**Present**

- Dashboard counts pending and accepted incoming transfers.
- Pending transfers, accept/reject actions, transfer history, and batch
  availability are exposed through `/api/collectors/`.
- A Collector can initiate a full-batch transfer to a Factory.

**Gaps and blockers**

- There is no public directory/search endpoint for eligible verified
  Collectors, Factories, or Labs. The organization list only returns the
  caller's own organization to ordinary users. The transfer screen selects a
  verified Collector/Factory, while the transfer API requires `to_party` as a
  user database primary key. Add a role-aware, verified-recipient lookup (or
  equivalent) that returns stable API identifiers and display-safe fields.
- `GET /api/collectors/available-batches/` returns all non-rejected,
  non-consumed batches once a Collector profile exists; it is not scoped to
  owner or organization. This is a tenant data-exposure risk and should be
  fixed before exposing this screen to real users.
- The transfer design exposes editable quantity, but transfer logic rejects
  anything other than the full available batch quantity. Either make the
  client contract explicitly whole-batch or design a real split-lot/custody
  model; changing only the quantity check would break ownership and
  traceability invariants.
- Transfer records do not store carrier/vehicle, IoT sensor, route,
  temperature/humidity telemetry, seal, handover PIN/signature, or a generated
  receipt. These must not be rendered as real backend data.
- The transfer serializer uses all model fields. Foreign keys are represented
  by related database keys rather than nested batch/user/organization
  summaries. The batch FK is not the human-facing `batch_id` string, so the
  UI needs another lookup and cannot safely treat it as that identifier.
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

- There is no Lab directory/list endpoint for a Farmer or Collector to obtain
  eligible `laboratory_id` values. The ordinary organization list cannot
  provide it.
- Test result measures in the design (analyte, method, observed value, unit,
  threshold, pass/fail, instrument, calibration, signed assessor) are not
  structured fields or a validated JSON contract. Arbitrary JSON/text does
  not guarantee the response shape needed by assay tables or filters.
- No individual lab-test detail route or server-side request/history filters
  exist. The response exposes related database keys rather than a nested
  human-readable batch identifier/profile.
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

- `ManufacturingRecord` only stores product name, process date/description,
  summed input/output quantities, unit, status, and remarks. Facility line,
  shift, SOP, solvent/method, target yield, temperature/pressure/flow
  telemetry, QC reviewer, and typed process parameters are not persisted.
- The UI's Save Draft behavior is unsupported. Manufacturing creation runs
  immediately, marks the record completed, and consumes inputs; there are no
  draft/start/complete/cancel endpoints.
- `ManufacturingRecordSerializer` does not include reverse input-batch links.
  The manufacturing detail response therefore cannot populate the selected
  input list/quantities without another API.
- Product metadata such as expiry is supported by the separate product
  endpoint, not the manufacturing endpoint. The workflow is two-step:
  create manufacturing record, then create one or more Products.
- Product list/detail responses omit `ProductBatch` input links. Although
  these links exist in the database, they are not included in
  `ProductSerializer`.
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
- Public verification does not return assay measurements, certificate
  contents/download link, GPS coordinates, rich custody actors/signatures,
  or a blockchain proof. The batch timeline endpoint is authenticated and is
  not a substitute for public disclosure.
- Product image and QR asset routes require the product UUID, while the QR
  reference lookup response does not return it. For image display, add a
  public asset URL to the verification response or return the needed asset
  metadata.
- Define a privacy-reviewed public response schema before exposing more
  farmer, location, organization, lab, or certificate information.

## API response contract notes

The following response shapes are confirmed from the current views and
serializers; they should be treated as the integration contract until explicit
response serializers are added.

| Endpoint | Current shape / limitation |
|---|---|
| `POST /api/auth/login/` | `{"user": UserSerializer, "tokens": {"access": "...", "refresh": "..."}}` |
| `POST /api/auth/register/` | `{"detail": "Registration successful. Verify your email with the OTP."}`; OpenAPI currently claims a `UserSerializer` response |
| Role dashboards | Role-specific flat count objects; not a common dashboard schema |
| List endpoints | Page-number pagination, default page size 20; many list endpoints have no search/order filters |
| Transfer list/action | `TransferEventSerializer(fields="__all__")`; related fields are database keys, not nested display objects |
| Lab test list/action | `LabTestSerializer(fields="__all__")`; certificate file is write-only and `certificate_available` is supplied |
| Manufacturing create/detail | `ManufacturingRecordSerializer(fields="__all__")`; reverse `input_batches` are omitted |
| Product list/create/detail | `ProductSerializer(fields="__all__")` plus image/QR asset URLs; reverse product input links are omitted |
| Batch history | `{"batch": HerbBatchSerializer, "history": [...]}`; event entries vary by `event_type` and are not represented by a single declared event schema |
| Public verify | `verification_status`, `product`, `manufacturing`, `input_herb_batches`; no full measurement/certificate payload |
| Factory receive | Returns `{"detail": "Batch received by factory.", "batch_id": "..."}`; OpenAPI currently documents `ReceiveBatchSerializer` as the response |

Several `@extend_schema` declarations use generic `OpenApiTypes.OBJECT` or
`responses={200: None}` for endpoints with meaningful JSON bodies. That leaves
Swagger/OpenAPI less useful than the real responses. Make explicit response
serializers for stable frontend integration.

## Prioritized backend work

### P0 — resolve before real multi-organization use

1. **Scope Collector batch visibility.** Restrict availability to an explicit
   business rule for batches visible/transferable to that Collector. Add tests
   proving another tenant's batches are not exposed.
2. **Add verified participant discovery.** Provide paginated, role-filtered
   recipient and Lab choices with stable identifiers and minimal display
   fields. Do not expose arbitrary users or unverified organizations.
3. **Resolve whole-batch transfer UX contract.** Keep whole-batch semantics
   explicit or design split-batch inventory/custody in the schema first.

### P1 — required for the displayed detail and data-entry flows

4. Add typed harvest metadata and a field-evidence model/upload workflow for
   photos/documents and validated metadata. Decide whether EXIF extraction is
   actually required and define accepted media/size limits.
5. Add structured Lab measurements and report metadata, or publish a strict
   versioned JSON schema for `test_parameters`. Add test detail and useful
   filters.
6. Add typed manufacturing process/run fields and a real lifecycle if drafts,
   process completion, QC sign-off, or telemetry are required. Otherwise
   remove unsupported behaviors from the backend contract.
7. Expose nested/stable response data: batch string IDs, recipient labels,
   test summaries, manufacturing inputs, and product input links. Add detail
   endpoints where list responses are insufficient.
8. Correct OpenAPI responses and add response-schema tests. Include explicit
   pagination, error/status semantics, and multipart upload definitions.
9. Decide and document the public verification payload/privacy policy,
   including whether product assets and certificates should be linkable
   publicly.

### P2 — quality, operations, and alignment

10. Add onboarding status aggregation and/or staff review actions if the custom
    panel is the intended approval tool. Existing model statuses can be
    edited in Django Admin.
11. Add dashboard aggregates/recent records and search/order filters only for
    data the backend actually stores.
12. Model true per-product input allocation if the product traceability screen
    needs quantitative lineage. Keep source-batch provenance distinct from
    measured mass balance.
13. Fix the debug OTP constant/test mismatch (`666666` implementation versus
    `098765` test expectation).
14. Keep blockchain fields as placeholders until a real integration exists.
    Never return a fabricated transaction, signature, hash, block, or
    telemetry value to satisfy a visual element.

## Verification performed

- Reviewed the Stitch page's screen inventory and backend route, view,
  serializer, model, permission, and admin implementations.
- `python manage.py spectacular --file ... --validate`: passed.
- `python manage.py makemigrations --check --dry-run`: no model/migration
  drift detected.
- Targeted tests for the two debug universal-OTP flows: both fail because
  responses are HTTP 400 instead of HTTP 200.
- No frontend files were read, tested, or changed.

For current route and business-flow details, see
[PROJECT_GUIDE.md](PROJECT_GUIDE.md). The runtime OpenAPI schema and
[config/urls.py](../config/urls.py) remain authoritative for the actual API
surface.
