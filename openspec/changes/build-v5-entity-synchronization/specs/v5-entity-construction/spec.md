## ADDED Requirements

### Requirement: V5 SHALL construct canonical entities from declared sources
V5 SHALL retrieve declared runtime-data and knowledge-base inputs after service startup, map them to entities using only the existing V4 schema, validate required fields, deterministically merge eligible records, and reject invalid or conflicting batches before publication. V5 SHALL NOT add source provenance, version, timestamp, snapshot, or `canonical` fields to entities.

#### Scenario: Compatible source records are built
- **WHEN** both declared sources return valid records for a refresh
- **THEN** V5 produces a deterministic batch of V4-schema entities with entity count and validation summary.

#### Scenario: A canonical conflict is detected
- **WHEN** source records produce incompatible authoritative fields or duplicate active normalized entity words
- **THEN** V5 rejects the batch, publishes no partial replacement, and returns a sanitized conflict diagnostic.

### Requirement: V5 SHALL publish complete builds in idempotent batches
V5 SHALL write only a fully validated canonical build as a candidate data snapshot through an Entity Data Service write port, reconcile it, and atomically switch it to the current snapshot. A build identifier and idempotency key SHALL ensure repeated publication of the same build does not duplicate entities. Daily snapshots SHALL NOT create or imply a new V5 software version.

#### Scenario: A validated build is retried
- **WHEN** publication is retried with the same build identifier after a retryable delivery failure
- **THEN** the publish port receives the same idempotency identity and the resulting data snapshot is not duplicated.

#### Scenario: One source fails before publication
- **WHEN** a required source cannot be retrieved or decoded
- **THEN** V5 does not switch the current snapshot and preserves the previously successful data snapshot.
