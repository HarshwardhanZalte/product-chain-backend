# Security and Business-Logic Review

**Review date:** 2026-11-21
**Scope:** Django backend source, models, serializers, views, settings, admin
interfaces, seed command, and tests.

This is a defensive source review. No exploit execution or runtime code changes
were performed. Findings and recommended remediations are summarized here.

## Remediation follow-up

All findings and the listed additional gaps have been addressed with focused
changes and regression tests. The requested universal OTP alternative remains
`098765`, but it is accepted only when `DJANGO_DEBUG=True`. Production mode
defaults to `DEBUG=False`, requires a strong secret and explicit allowed hosts,
and enables HTTPS/cookie/HSTS protections by default. Private organization and
laboratory files use authenticated download endpoints; generic media serving is
disabled.

The implementation also restricts organization assignment and access, gates
business mutations on approved organizations/profiles, requires accepted
full-quantity transfer events for custody changes, validates manufacturing
inputs and product-output allocations, requires approved latest lab tests for
public `VERIFIED` status, enables throttling, fixes QR URLs, implements batch
history timelines, and guards seed data to debug mode.

Validation after remediation: full Django test suite passed (32 tests), Django
system check passed, OpenAPI validation passed, and no model migrations were
required. Production deployment checks passed with a strong temporary key; a
weak local `.env` key is intentionally rejected when `DEBUG=False`.

## Findings from the pre-remediation review

| # | Severity | File | Lines | Finding | Confidence |
|---|----------|------|-------|---------|------------|
| 1 | 🔴 CRITICAL | `users/services.py`, `users/views.py` | services.py:10, 63-74; views.py:228-246 | Universal OTP fallback bypasses normal verification and password-reset checks outside debug mode. Restrict it to DEBUG only. | 10/10 |
| 2 | 🟠 HIGH | `users/serializers.py`, `users/views.py`, `organization/views.py`, `organization/serializers.py` | serializers.py:8-18; views.py:43-59; org views.py:31-38; org serializers.py:6-15 | Public registration can attach to an existing organization, then organization membership grants access to retrieve/update organization fields. Use an approved membership flow and field allowlists. | 10/10 |
| 3 | 🟠 HIGH | `factory/views.py` | 79-93 | Factory can claim any approved batch without a matching accepted transfer. Require and validate the custody handoff before changing ownership. | 10/10 |
| 4 | 🟡 MEDIUM | `factory/views.py` | 112-131, 145-152 | Duplicate manufacturing inputs overwrite in the batch map after being summed, so the recorded total can differ from inventory deductions. Reject or aggregate duplicate batch IDs before validation. | 10/10 |
| 5 | 🟡 MEDIUM | `collector/views.py`, `collector/serializers.py` | views.py:104-117; serializers.py:10-30 | Transfer acceptance changes whole-batch ownership without quantity accounting or revalidating sender ownership. Define whole/partial transfer semantics and lock/revalidate on acceptance. | 10/10 |
| 6 | 🟡 MEDIUM | `product/views.py` | 153-162 | Public verification may report `VERIFIED` when the latest test is pending. Require approved latest tests for every input batch. | 9/10 |
| 7 | 🟡 MEDIUM | `product/views.py`, `product/serializers.py`, `product/models.py` | views.py:54-72; serializers.py:6-20; models.py:32-36 | Product quantity is not reconciled against manufacturing output, and a completed record can be reused. Enforce output allocation limits or one product per record. | 9/10 |
| 8 | 🟠 HIGH* | `config/settings.py` | 25-33 | Development secret and `DEBUG=True` defaults are unsafe if production overrides are missing. Fail closed and require secure production settings. | 9/10 |
| 9 | 🟡 MEDIUM* | `users/management/commands/seed_test_data.py` | 26-30, 93-100 | Seed command uses a known default password and can create a superuser. Restrict to development or require explicit credentials/confirmation. | 9/10 |
| 10 | 🟡 MEDIUM* | `users/permissions.py`, `organization/views.py`, role views | permissions.py:13-20; organization/views.py:10-15 | Organization/profile verification is not consistently enforced before role actions. Define the approval policy and enforce it server-side. | 8/10 |
| 11 | 🟡 MEDIUM* | `lab/serializers.py`, `lab/views.py` | serializers.py:15-21; views.py:110-141 | Certificate upload serializer does not apply the model's document validator. Validate uploads at the API boundary and keep private media private. | 8/10 |
| 12 | ⚪ LOW | `users/tests.py`, `users/services.py`, `users/management/commands/seed_test_data.py` | tests.py:61-73; services.py:10; seed_test_data.py:318-326 | OTP test/seed values disagree with the current fallback constant, causing unreliable test data and a failing expectation. Remove fallback and test generated OTPs. | 10/10 |

`*` Conditional or policy-dependent severity.

## Additional gaps observed during review

- Batch history currently returns the batch record, not a combined event timeline.
- QR generation embeds a singular product URL while the mounted verification
  route is plural; generated QR links may not resolve.
- Throttle rates are configured, but throttle classes are not enabled.
- Factory receipt is not represented as a `TransferEvent`.
- Public verification returns certificate availability rather than a controlled
  public certificate reference.
- Development media serving should not be used for private production files.

## Review checks

- `python manage.py check`: passed.
- OpenAPI generation/validation: passed.
- Review test run: 11 passed, 1 failed. The failing test used an OTP that did
  not match the current fixed fallback.

## Remediation order

1. Restrict the universal OTP alternative to debug mode and enforce normal OTP
   validation in production.
2. Restrict organization assignment and access.
3. Enforce accepted handoffs for factory and collector custody changes.
4. Fix duplicate manufacturing input accounting and product output allocation.
5. Require approved latest lab tests for `VERIFIED` public status.
6. Make production settings fail closed and protect the seed command.
7. Enforce organization approval, upload validation, and private media handling.
8. Correct QR URLs and implement a true traceability event history.
