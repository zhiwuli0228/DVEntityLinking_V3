## ADDED Requirements

### Requirement: V4 public module contract SHALL remain compatible
V4.1 SHALL preserve V4 public request and response fields, state values, error semantics, and synchronous/asynchronous entry semantics. New public fields SHALL be optional and have defaults.

#### Scenario: Existing V4 request is processed
- **WHEN** a caller submits a valid V4-shaped request
- **THEN** V4.1 accepts it and returns a response containing all established V4 fields.

#### Scenario: A compatibility-sensitive result is produced
- **WHEN** a V4 golden input produces linked, ambiguous, partial, no-match, bypass, invalid-input, or dependency-failed behavior
- **THEN** V4.1 returns the corresponding established state and compatible mention/candidate semantics.

### Requirement: Compatibility evidence SHALL be inspectable
The repository SHALL store a machine-readable manifest of the supported public contract and tests that validate it independently of module-generated traces.

#### Scenario: Contract verification runs
- **WHEN** the V4.1 compatibility test suite runs
- **THEN** it validates the manifest and black-box expected response projection.
