## 1. V5 baseline and contracts

- [x] 1.1 Create independent V5 IR/SR, an Entity Build Plugin boundary, source inventory, and traceability register linked to this change and the V4/V4.1 compatibility boundary.
- [x] 1.2 Define typed V4-schema entity build input/output, safe aggregate diagnostics, and Entity Data batch-update/atomic-switch port contracts without adding entity fields.
- [x] 1.3 Define unversioned `QueryRecallRequest` / `QueryRecallResult` public contracts and a compatibility adapter for legacy `*V1` DTOs; add tests proving V4 neither imports nor invokes the Entity Build Plugin while status semantics remain unchanged.
- [x] 1.4 Define the independently composable Query Recall Facade contract and a validated, hot-reloadable recall-policy configuration schema for LLM participation, fallback, Top-K, and entity-type scope.

## 2. REST request boundary

- [x] 2.1 Implement the independent long-lived declarative REST request tool with method, URL, params/body, authentication reference, timeout, retry, idempotency configuration, and injectable HTTP/platform-IR transports.
- [x] 2.2 Implement safe response decoding, bounded retry classification, structured transport errors, and credential/payload-safe trace projection.
- [x] 2.3 Refactor V4 `IrEntityDataClient` and `RestEntityDataClient` to use the shared tool without changing their public Entity Data contract; add tests proving V4/V5 adapters use the tool exclusively, including timeout, retry, invalid schema, and no-secret-leak cases.

## 3. Query recall facade and runtime policy

- [x] 3.1 Implement the Query Recall Facade with raw query as its only required input, unversioned public DTOs, validated `use_llm`/`top_k` overrides, and compatibility-adapter response projection.
- [x] 3.2 Implement atomic recall-policy configuration reload that preserves the last valid policy on parse or validation failure.
- [x] 3.3 Add tests for default policy, per-request override precedence, dynamic LLM/Top-K application, invalid reload retention, unversioned public DTOs, and legacy status/candidate compatibility.

## 4. Entity construction and publication

- [x] 4.1 Implement runtime-data and knowledge-base source adapters that map declared remote data into V4-schema entities without adding entity fields.
- [x] 4.2 Implement deterministic canonical entity construction, source-priority merge, required-field validation, active normalized-word conflict rejection, and safe build reporting.
- [ ] 4.3 Implement the idempotent Entity Data candidate-snapshot, reconciliation, and atomic-switch adapter; failure handling must preserve the last successfully published data snapshot.
- [ ] 4.4 Add unit and integration tests for valid builds, source failure, validation conflict, publish retry/idempotency, and V4 read-side isolation.

## 5. Lifecycle scheduling and operations

- [ ] 5.1 Implement lifecycle-triggered initial refresh within the Entity Build Plugin, with explicit host opt-in, blocking/background mode, and observable refresh state.
- [ ] 5.2 Implement configurable-time-zone daily-midnight scheduling with single-process overlap prevention and safe skipped-run evidence.
- [ ] 5.3 Add deterministic clock/scheduler tests for startup, midnight execution, overlap, validation failure, previous-data-snapshot retention, and no software-version change on refresh.
- [ ] 5.4 Document external-source onboarding, Entity Data write authorization, multi-instance leader requirement, dry-run/rollback procedure, and operational evidence fields.

## 6. Acceptance

- [x] 6.1 Run focused V5 facade/plugin, V4/V4.1 isolation/compatibility, and complete regression suites; record results in V5 traceability.
- [ ] 6.2 Execute an approved fixture-based end-to-end build/candidate-snapshot/atomic-switch dry-run and record only sanitized counts, snapshot references, and outcomes.
