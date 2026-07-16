## ADDED Requirements

### Requirement: Repository-wide canonical field migration
The system SHALL use `entity_name`, `desc`, and `alias` as the canonical entity field names in persisted entity artifacts, internal entity records, public API projections, and frontend adapter inputs. It SHALL NOT emit `canonical_name`, `description`, or `aliases` in the migrated entity contract.

#### Scenario: Load migrated V3 artifacts
- **WHEN** the V3 Gauss and Redis mock artifacts use the canonical entity schema
- **THEN** startup validation and entity linking SHALL complete without relying on legacy entity field names

#### Scenario: Detect stale legacy artifact fields
- **WHEN** a structured-entity artifact supplies legacy-only descriptive field names instead of the required canonical fields
- **THEN** startup validation SHALL fail closed and identify the missing canonical fields

### Requirement: Alias-to-cache consistency after migration
The system SHALL construct and validate Redis entity-word entries from `entity_name` and confirmed values in `alias` only. A cache entry MUST reference an existing entity ID and MUST match either that entity's normalized name or a normalized confirmed alias.

#### Scenario: Link through a migrated confirmed alias
- **WHEN** a query contains a confirmed value from an entity's `alias` list
- **THEN** the Redis-backed linking flow SHALL resolve the entity's stable ID and return the canonical entity record

#### Scenario: Reject an unconfirmed cache word
- **WHEN** a Redis entity-word entry does not match the referenced entity's name or confirmed alias
- **THEN** cache loading SHALL fail closed and exclude the invalid mapping from the linking flow
