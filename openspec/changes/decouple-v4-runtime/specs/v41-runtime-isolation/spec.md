## ADDED Requirements

### Requirement: Default runtime SHALL exclude historical assets
The default V4.1 public module composition SHALL not import, instantiate, or use `dv_entity_linking.legacy`, V3 Mock clients, Redis/Gauss Mock assets, or historical JSON catalogs as runtime data sources.

#### Scenario: Default factory is inspected
- **WHEN** the production package and public factory are scanned
- **THEN** no denied historical runtime dependency is found.

#### Scenario: Entity data dependency fails
- **WHEN** the configured Entity Data client fails during a linking request
- **THEN** the module returns its existing structured dependency-failure semantics and SHALL NOT fall back to historical data.

### Requirement: Historical assets SHALL remain explicit test or migration inputs
Historical implementations and fixtures SHALL be usable only through explicit test or migration-tool injection and SHALL NOT be selected by default configuration.

#### Scenario: A compatibility test uses a historical fixture
- **WHEN** a test explicitly supplies a historical fixture
- **THEN** the fixture is accepted for comparison without changing the default runtime composition.
