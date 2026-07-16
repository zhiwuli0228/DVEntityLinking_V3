## 1. Runtime isolation and compatibility baseline

- [x] 1.1 Add a V4.1 production-runtime dependency policy and a test that rejects historical runtime imports/references outside explicit test or migration scopes.
- [x] 1.2 Add a machine-readable V4 public-contract manifest and black-box compatibility tests for the established request/response fields and status set.
- [x] 1.3 Verify the default factory has no historical data fallback and add a regression test for dependency failure behavior.

## 2. Migration and configuration validation

- [x] 2.1 Implement canonical entity migration validation with alias-word projection, active-key conflict detection, relationship validation, and sanitized dry-run reporting.
- [x] 2.2 Implement V4.1 configuration validation/migration that rejects prohibited historical runtime settings and supports dry-run diagnostics.
- [x] 2.3 Add unit tests for valid migration, conflict/relationship failure, report safety, and deprecated configuration rejection.

## 3. Traceability and verification

- [x] 3.1 Add V4.1 traceability, compatibility-difference, and historical-asset deprecation registers linked to OpenSpec task and test IDs.
- [x] 3.2 Run focused V4/V4.1 tests and the complete test suite; record the commands and results in the traceability register.
- [x] 3.3 Review the implementation against all four V4.1 capability specifications and close or register any remaining approved difference.
