## Why

V4 has completed the module and data-service boundary transition, but the implementation does not yet satisfy all of the V4 IR/SR commitments. In particular, lifecycle policy, IR contract, componentized capability migration, and a few LLM/async semantics are either missing or contradictory, so passing regression tests alone cannot be used as final acceptance evidence.

## What Changes

- Define and implement the V4 production lifecycle contract: health capability plus effective `FAIL_FAST` and `DEGRADED` startup policy.
- Make the Entity Data IR URL and platform client the sole production transport contract; remove residual REST terminology and align the request-envelope schema.
- Migrate the V1–V3 capability matrix into independently testable V4 domain components, beginning with intent, recognition, type resolution, candidate resolution, selection, aggregation, and safe trace construction.
- Align LLM rerank fallback semantics with the preserved legacy behavior: an invalid/unavailable reranker retains deterministic Top-K ambiguity regardless of `allow_fallback`.
- Make the asynchronous facade non-blocking or explicitly constrain it to the supported synchronous contract.
- Add black-box and contract tests for every repaired requirement, including negative tests that reject former invalid implementations.

## Capabilities

### New Capabilities

- `v4-runtime-lifecycle`: V4 module startup health checks and deterministic `FAIL_FAST`/`DEGRADED` behavior.
- `v4-ir-client-contract`: Production-only IR URL plus platform-client transport contract and its stable envelope.
- `v4-domain-capability-migration`: Independently testable V1–V3 linking capabilities in the V4 domain pipeline.
- `v4-llm-and-async-semantics`: Preserved LLM fallback behavior and non-blocking asynchronous module entry.
- `v4-design-implementation-verification`: Traceable design-to-code acceptance matrix and black-box regression gates.

### Modified Capabilities

None; this repository has no baseline OpenSpec capability specifications.

## Impact

Affected areas include `src/dv_entity_linking/module.py`, domain ports and recognition/pipeline modules, the IR client, the public README, V4 IR/SR documents, and V4 contract tests. The public factory retains its required IR URL and platform-client inputs; the change may make previously inert configuration fields operational and will not reintroduce V3 Mock, Redis, or local persistent lookup data to the V4 runtime chain.
