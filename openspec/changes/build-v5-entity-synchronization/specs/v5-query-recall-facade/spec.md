## ADDED Requirements

### Requirement: V5 SHALL provide a simple external query recall facade
V5 SHALL provide an independently composable query recall facade whose required input is only the raw query. Its public request and result types SHALL be named `QueryRecallRequest` and `QueryRecallResult` and SHALL NOT contain version suffixes. The facade MAY accept only approved optional overrides for LLM participation and candidate Top-K, and SHALL delegate through a compatibility adapter without exposing legacy `*V1` DTOs, HTTP configuration, or LLM adapters.

#### Scenario: Default recall is requested
- **WHEN** a caller invokes recall with only a non-empty raw query
- **THEN** the facade applies the current validated configuration and returns a `QueryRecallResult` containing compatible mention, candidate, status, error, and degradation semantics.

#### Scenario: Approved call override is supplied
- **WHEN** a caller supplies a valid `use_llm` or `top_k` override
- **THEN** that override takes precedence for that request only and does not mutate the active configuration.

### Requirement: Query recall policy SHALL be dynamically reloadable
V5 SHALL load LLM participation, fallback, Top-K, and allowed entity-type policy from a configuration file. A configuration reload SHALL validate the complete file before atomically applying it to subsequent requests; an invalid reload SHALL retain the last valid configuration.

#### Scenario: Valid configuration is reloaded
- **WHEN** the configured policy file changes to a valid value
- **THEN** subsequent recall requests use the new policy without restarting the host.

#### Scenario: Invalid configuration is reloaded
- **WHEN** the configured policy file cannot be parsed or violates validation rules
- **THEN** the facade continues using the last valid policy and emits only a sanitized reload diagnostic.
