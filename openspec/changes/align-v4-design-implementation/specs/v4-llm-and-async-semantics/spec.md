## ADDED Requirements

### Requirement: Rerank failure preserves deterministic ambiguity
The S5 reranker SHALL only select an existing confirmed candidate and SHALL preserve deterministic Top-K ambiguity on timeout, invalid schema, invalid ID, or low confidence regardless of `allow_fallback`.

#### Scenario: Strict request receives invalid rerank output
- **WHEN** `allow_fallback` is false and the reranker returns an invalid candidate ID
- **THEN** the module SHALL return deterministic `ambiguous` candidates rather than `dependency_failed`

### Requirement: Async entry does not block the event loop
The public `link_async` entry SHALL preserve `link` response semantics without executing the synchronous pipeline on the caller event loop.

#### Scenario: Concurrent async caller
- **WHEN** `link_async` waits for a blocking synchronous Entity Data client
- **THEN** another scheduled event-loop task SHALL continue to run before the response completes
