## ADDED Requirements

### Requirement: Production transport uses IR URL and platform client
The V4 public factory SHALL use only `entity_data_ir_url` and a platform `InternalRouteClient` for production Entity Data calls.

#### Scenario: Missing production dependency
- **WHEN** the factory is called without a non-empty IR URL or platform client
- **THEN** it SHALL fail configuration and SHALL not load Mock, Redis, Gauss JSON, or a direct HTTP client

### Requirement: IR envelope is stable
The IR client SHALL send operation-specific read fields inside the documented `payload` object and SHALL validate operation, status, data version, and response schema.

#### Scenario: Batch read version pinning
- **WHEN** a word recall returns a data version
- **THEN** the following detail read SHALL send that version in its operation payload and reject a mismatched response
