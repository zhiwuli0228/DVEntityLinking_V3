## ADDED Requirements

### Requirement: Canonical entity record
The system SHALL represent every structured entity with `entity_id`, `entity_name`, `desc`, `alias`, `entity_type`, `attributes`, and `relationships`. `entity_id`, `entity_name`, and `desc` MUST be non-empty strings; `alias` MUST be a list of strings; `entity_type` MUST be a supported entity type; `attributes` MUST be an object; and `relationships` MUST be a list.

#### Scenario: Load a canonical entity record
- **WHEN** a structured-entity artifact contains all required canonical fields with valid values
- **THEN** the structured store SHALL load the entity and expose the same canonical fields to consumers

#### Scenario: Reject a malformed canonical entity record
- **WHEN** a structured-entity artifact omits a required canonical field or supplies it with an invalid type
- **THEN** startup validation SHALL fail closed with a structured schema error

### Requirement: Entity attributes extension point
The system SHALL accept `attributes` as JSON-compatible entity-type-specific metadata with string keys. It MUST preserve valid attribute values in internal records and safe API projections, subject to existing secret and unsafe-value filtering rules.

#### Scenario: Expose valid attributes
- **WHEN** a loaded entity contains JSON-compatible attributes
- **THEN** a safe entity projection SHALL include the permitted attribute values without converting them into top-level common fields

#### Scenario: Reject unsafe attribute content
- **WHEN** an entity contains an attribute value that violates the repository's safe-value rules
- **THEN** the system SHALL omit the unsafe value from public projection and SHALL not expose it in run records or API responses

### Requirement: Typed entity relationships
The system SHALL represent each relationship as an object with non-empty `relation_type` and `target_entity_id` strings. Each `target_entity_id` MUST reference an entity in the same structured-entity dataset.

#### Scenario: Load a valid directed relationship
- **WHEN** an entity relationship has a valid relation type and names an existing target entity ID
- **THEN** the source entity SHALL expose that directed relationship

#### Scenario: Reject a dangling relationship target
- **WHEN** an entity relationship references an entity ID not present in the structured-entity dataset
- **THEN** startup validation SHALL fail closed with a structured dangling-reference error
