## Context

V4 already exposes a module facade and an Entity Data IR client, but the repository still contains V1–V3 implementations and fixtures beside V4. V4.1 must make the default runtime path independently auditable without changing its public response semantics. Existing V4 tests are the starting compatibility baseline; historical assets remain useful only when explicitly injected by tests or migration tools.

## Goals / Non-Goals

**Goals:**

- Make default V4.1 composition demonstrably independent of historical runtime assets.
- Preserve the V4 public facade and observable linking semantics.
- Provide deterministic, dry-run-first entity/config migration validation.
- Add machine-readable traceability for compatibility differences and deprecated assets.

**Non-Goals:**

- Replace the Entity Data Service, alter the Entity Data IR, or introduce a new matching algorithm.
- Delete historical implementations or make unverified production data changes.
- Add long-lived runtime dual-read, dual-write, or fallback to V3 Mock data.

## Decisions

### 1. Enforce runtime isolation with a source-level allowlist test

The production package will be scanned for imports and string references to a defined legacy denylist. Test and migration roots are exempt. This is preferred over a directory move because it protects the actual execution boundary and can be kept in CI. A runtime monkeypatch-only test was rejected because it cannot reveal dormant imports or future accidental dependencies.

### 2. Freeze compatibility through a manifest and black-box fixtures

A checked-in manifest records the stable public request/response fields and state set. Tests use explicit V4-shaped inputs and expected response projections instead of comparing two executions of the same code. This catches contract drift while allowing internal V4.1 refactoring. Copying legacy DTOs into the new runtime was rejected because it would preserve the dependency being removed.

### 3. Keep migration pure, local, and dry-run by default

The migration module transforms canonical entity records into a validated publication bundle and emits a sanitized report. It does not call a live Entity Data Service, write a database, or read credentials. A caller may pass the validated bundle to its authorized publishing workflow. This separates safe repository work from deployment authority and makes migration repeatable.

### 4. Reject obsolete configuration explicitly

V4.1 config migration accepts known V4 values and reports deprecated Mock/Redis/Gauss/Flask-runtime keys. Production validation rejects deprecated keys instead of silently ignoring them. Silent translation was rejected because it can accidentally reactivate historical runtime paths.

### 5. Record operational evidence as documents, not executable runtime state

Traceability, compatibility differences and deprecation records live under `docs/baselines/v4.1/`. They link OpenSpec task IDs, tests and migration reports; no deployment or data change occurs merely by creating them.

## Risks / Trade-offs

- [The exact V4 acceptance commit is not yet identified] → Treat current checked-in V4 contracts as the temporary baseline and keep `AR-V4.1-001` open.
- [Historical callers may use undocumented internals] → Scan repository callers, require explicit compatibility records for known exceptions, and retain history as test-only assets.
- [Canonical data exports can be malformed] → Validate every record and projection before publishing; dry-run is the default and validation failures produce no write action.
- [Static scanning can have false positives] → Scan Python production roots and import/reference patterns only; tests prove the intended exemptions.

## Migration Plan

1. Add isolation, manifest, migration and traceability primitives with unit tests.
2. Run migration validation in dry-run mode against repository fixtures or an authorized canonical export.
3. Compare V4.1 results with approved V4 golden cases; register any intentional difference.
4. Deploy only through the host's authorized release path, first in mirror/limited traffic mode.
5. If behavior or dependency failures exceed the agreed threshold, route traffic back to the validated V4 release; do not perform unverified reverse data migration.

## Open Questions

- Which tag or commit is the formal V4 acceptance baseline?
- Which external hosts require an explicit `CMP-V4.1-*` record?
- Who owns the authorized Entity Data Service publish and rollback procedure?
