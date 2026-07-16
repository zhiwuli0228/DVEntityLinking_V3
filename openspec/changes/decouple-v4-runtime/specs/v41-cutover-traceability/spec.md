## ADDED Requirements

### Requirement: V4.1 evidence SHALL be traceable
V4.1 SHALL maintain traceability from requirement and design IDs to implementation tasks, tests, migration evidence, compatibility differences, and acceptance records.

#### Scenario: A V4.1 requirement is reviewed
- **WHEN** a reviewer selects an IR or SR identifier
- **THEN** the traceability record identifies its implementing task and verification evidence.

### Requirement: Historical assets and differences SHALL be governed
Every retained historical runtime-adjacent asset and every compatibility difference SHALL have an identifier, owner or disposition, scope, and deletion or approval condition.

#### Scenario: A legacy asset is retained
- **WHEN** a historical asset is retained for regression or audit
- **THEN** its record states that it is non-runtime, its purpose, and its removal condition.
