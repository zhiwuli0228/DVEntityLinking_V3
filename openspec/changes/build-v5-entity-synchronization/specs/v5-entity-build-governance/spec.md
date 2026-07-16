## ADDED Requirements

### Requirement: V5 entity builds SHALL have auditable governance artifacts
V5 SHALL maintain independent IR/SR, source inventory, build-to-publication traceability, compatibility records, and operational evidence without storing secrets, full upstream payloads, or production URLs in repository documentation.

#### Scenario: A V5 build is reviewed
- **WHEN** a reviewer selects a V5 requirement or build identifier
- **THEN** the traceability record identifies the source class, validation result, publication outcome, tests, and applicable rollback target.

### Requirement: V5 SHALL preserve V4 read-side compatibility and V4.1 isolation
V5 SHALL be packaged and composed as an independently installable Entity Build Plugin. V5 SHALL not change V4 public linking DTO/status semantics, and V4 SHALL NOT import, instantiate, or invoke V5 plugin classes. The V5 build pipeline SHALL NOT introduce historical assets into the default V4/V4.1 read-side runtime.

#### Scenario: V5 is enabled beside V4 linking
- **WHEN** a host enables V5 entity construction and V4 linking
- **THEN** the V4 public contract remains compatible and default read-side dependency-isolation checks continue to pass.

#### Scenario: The build plugin is migrated to the data service
- **WHEN** a host replaces the local V5 plugin with an Entity Data Service-hosted implementation of its published ports
- **THEN** V4 linking code and its public contract require no modification.
