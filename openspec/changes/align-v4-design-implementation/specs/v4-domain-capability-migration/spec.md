## ADDED Requirements

### Requirement: Capability matrix has independent V4 components
The V4 pipeline SHALL compose independently testable intent, recognition, type resolution, candidate resolution, mention selection, result aggregation, and safe trace components.

#### Scenario: Component substitution
- **WHEN** a test injects an approved replacement for one domain component
- **THEN** the facade SHALL preserve the public V1 DTO contract while using that component's observable decision

### Requirement: Type and candidate decisions preserve V1–V3 behavior
The type resolver and candidate resolver SHALL use request hints, confirmed word metadata, boundary/context evidence, source, priority, and valid extraction evidence without creating unconfirmed entity IDs.

#### Scenario: Cross-type ambiguous word
- **WHEN** one confirmed word maps to candidates of multiple types and no valid narrowing evidence exists
- **THEN** the result SHALL retain ordered Top-K candidates and return `ambiguous`
