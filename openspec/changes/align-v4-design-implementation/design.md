## Context

V4 already enforces a production factory boundary (IR URL plus platform client) and keeps V3 Mock out of that factory. The audit found remaining gaps between V4 IR/SR and implementation: lifecycle policy is inert, the IR protocol is described inconsistently, the capability matrix is not yet componentized, the IR document conflicts with preserved rerank behavior, and the async facade blocks the caller's event loop.

The module must continue to use the external Entity Data Service as its only data authority. `el_entity` and `el_entity_word` remain owned by that service; V4 does not introduce Redis, local persistent word stores, database access, or new LLM stages.

## Goals / Non-Goals

**Goals:**

- Turn every audited discrepancy into an observable requirement, implementation task, and automated verification.
- Make startup policy, IR protocol, V1–V3 capability migration, LLM fallback, and async behavior agree across IR, SR, README, code, and tests.
- Preserve the existing production factory boundary and historical LLM scope.

**Non-Goals:**

- Implement the Entity Data Service or its relational database schema in this repository.
- Reintroduce V3 Mock, Redis, Gauss JSON, or local persistent snapshots to V4 runtime.
- Add new LLM functions beyond legacy extraction and ambiguous-candidate reranking.

## Decisions

### Lifecycle is a port capability, not a hidden constructor side effect

Extend the V4 `EntityDataClient` port with a health operation and validate it only through the configured startup policy. `FAIL_FAST` rejects a failed/unavailable service at assembly; `DEGRADED` permits construction and returns the existing structured dependency failure when a request needs the service. This avoids an implicit network call for every direct test injection while making production behavior explicit.

Alternative: remove the policy and health statements from V4. Rejected because they are already part of the V4 configuration contract and are needed for reliable host integration.

### IR URL is the module's only production transport vocabulary

Rename remaining production-facing REST references to Entity Data IR. The IR envelope carries operation-specific fields consistently inside `payload`; the direct HTTP adapter stays test-only. This matches the platform-client implementation and prevents callers from treating the module as an HTTP client.

Alternative: promote the direct REST adapter as an equal production adapter. Rejected because it leaks deployment and transport concerns into host integration.

### Migrate capability matrix through narrow domain components

Introduce internal policy/component interfaces for intent, known/unknown recognition, type resolution, candidate resolution, mention selection, aggregation, and safe trace construction. The public facade remains unchanged and composes the default implementations. Each component receives only the information it needs and has a V1–V3 golden-case contract.

Alternative: retain helper functions in `module.py`. Rejected because it cannot demonstrate replaceability, isolate regressions, or trace matrix acceptance.

### Preserve deterministic rerank fallback and offer real async execution

Invalid/unavailable S5 output always preserves deterministic Top-K ambiguity, independent of `allow_fallback`; IR and SR use that single rule. `link_async` runs the synchronous pipeline outside the caller event loop until an async platform-client port is introduced, preserving response semantics without claiming a non-existent native async transport.

## Risks / Trade-offs

- [More internal components increase wiring] → Keep components internal, provide defaults, and preserve the one public facade.
- [FAIL_FAST can make startup unavailable during a remote outage] → Keep `DEGRADED` as an explicit configuration choice and test both paths.
- [Golden expectations may reveal historic inconsistencies] → Treat V1–V3 evaluated behavior and approved V4 IR/SR decisions as the source of truth; document any approved intentional deviation.
- [Async thread offload does not make the platform client asynchronous] → It prevents event-loop blocking while preserving the existing synchronous client contract.

## Migration Plan

1. Correct the IR/SR/README wording and establish the contract tests before changing behavior.
2. Add health to the port and IR adapter, then make factory policy observable.
3. Extract domain components one at a time behind default composition, preserving existing black-box tests after each extraction.
4. Add capability-specific golden cases and reject V4 completion until every matrix row is green.
5. Deploy with `DEGRADED` first where startup availability is required; use `FAIL_FAST` after Entity Data Service health is operationally proven. Roll back by selecting `DEGRADED`, not by restoring a local/mock data fallback.

## Open Questions

- The exact IR health operation/path and its contract version remain to be confirmed with the platform owner.
- The host platform may later expose a native async IR client; that can replace the thread-offload adapter without changing the public module API.
