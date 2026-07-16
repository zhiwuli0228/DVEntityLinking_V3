## ADDED Requirements

### Requirement: V4 and V5 remote interactions SHALL use the shared REST request tool
The REST request tool SHALL be an independent, long-lived infrastructure capability rather than a V5 plugin component. V4 Entity Data adapters and V5 application, source-adapter, and publisher classes SHALL delegate remote HTTP or platform-IR interaction to this one tool and SHALL NOT import or invoke an underlying transport client directly.

#### Scenario: A source adapter retrieves data
- **WHEN** a source adapter requests runtime or knowledge-base data
- **THEN** it supplies a declarative URL, request method, parameters/body, and security configuration reference to the REST request tool.

#### Scenario: A V4 Entity Data query is executed
- **WHEN** `IrEntityDataClient` or `RestEntityDataClient` executes an Entity Data operation
- **THEN** it delegates transport execution to the shared REST request tool and retains only Entity Data envelope mapping and schema validation.

### Requirement: The REST request tool SHALL normalize transport behavior safely
The REST request tool SHALL centrally apply timeout, bounded retry policy, authentication injection, response decoding, structured error mapping, and sanitized trace generation without exposing credentials, authorization headers, or complete upstream payloads.

#### Scenario: A retryable transport failure occurs
- **WHEN** a configured idempotent remote request returns a retryable transport failure
- **THEN** the tool retries only within its bounded policy and returns one structured success or failure result.

#### Scenario: A request fails permanently
- **WHEN** a remote request fails with a non-retryable status or invalid response schema
- **THEN** the tool returns a structured safe error without leaking the authentication value or raw payload.
