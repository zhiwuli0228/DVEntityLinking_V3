## ADDED Requirements

### Requirement: Every V4 design commitment has an acceptance mapping
The V4 IR/SR capability matrix SHALL map each runtime commitment to an implementation component and at least one independent automated verification.

#### Scenario: Acceptance audit
- **WHEN** V4 acceptance is evaluated
- **THEN** missing components, missing tests, or contradictory IR/SR/code semantics SHALL block acceptance

### Requirement: Historical assets remain comparison-only
V1–V3 Mock, Redis/Gauss JSON, and legacy Web assets SHALL be usable only by explicit test or migration wiring and SHALL not be a V4 default runtime authority.

#### Scenario: Production factory inspection
- **WHEN** the public V4 factory is exercised without valid production dependencies
- **THEN** it SHALL fail configuration rather than load a historical data asset
