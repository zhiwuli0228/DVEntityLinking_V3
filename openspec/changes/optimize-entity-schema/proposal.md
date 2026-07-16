## Why

The current entity model uses fixed names such as `canonical_name`, `aliases`, and `description`, and does not provide a controlled extension point for entity-type-specific metadata or entity-to-entity relationships. As the DV entity service expands beyond its V3 sample set, this limits schema evolution and makes downstream consumers depend on legacy field naming.

## What Changes

- Replace the public, persisted entity field names with `entity_name`, `desc`, and `alias`.
- Preserve `entity_id` as the stable entity primary key, although it is not a mutable descriptive property.
- Add `attributes` as an extensible object for entity-type-specific metadata.
- Add `relationships` as a list of typed links to target entity IDs.
- **BREAKING** Update entity data artifacts, storage validation, API projections, and frontend adapters to use the new field names and schema.
- Retain V3 safety guarantees: confirmed aliases only, cross-layer entity-ID consistency, fail-closed loading, safe API projection, and offline deterministic validation.

## Capabilities

### New Capabilities

- `extensible-entity-schema`: Defines the canonical entity schema, validation rules, extension-point semantics, and relationship reference rules.
- `entity-schema-migration`: Defines the repository-wide migration from the legacy entity field contract to the canonical schema.

### Modified Capabilities

<!-- No existing OpenSpec capability specifications are present in this repository. -->

## Impact

- Python models, storage adapters, catalog and linking flows, retrieval projections, Web/API serialization, and frontend adapters.
- V3 Gauss/Redis mock artifacts, golden cases, contract tests, and acceptance scripts.
- Current documentation and data-contract references that describe the legacy field names.
- No new external runtime dependency or default real DV/Redis/GaussDB connection is introduced.
