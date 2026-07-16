## Context

V3 currently represents structured entities with `entity_id`, `entity_type`, `canonical_name`, `aliases`, and `description`. The Gauss Mock validates those fields, the Redis Mock validates entity words against the canonical name or confirmed aliases, and Web/API projections expose the resulting records. This change replaces the descriptive field names and introduces controlled extension points without changing the offline-first, storage-backed linking architecture.

## Goals / Non-Goals

**Goals:**

- Establish one canonical entity schema: `entity_id`, `entity_name`, `desc`, `alias`, `entity_type`, `attributes`, and `relationships`.
- Keep `entity_id` stable for storage lookup, cross-layer consistency, and relationship targets.
- Support per-type metadata through `attributes` without relaxing validation of the common fields.
- Support explicit entity relationships while rejecting dangling or malformed targets at load time.
- Migrate repository data artifacts and public API/frontend projections atomically, with no legacy names emitted after migration.

**Non-Goals:**

- Connecting to real Redis, GaussDB, DV runtime interfaces, or a graph database.
- Defining a universal ontology for `attributes` keys or relationship types.
- Automatically inferring aliases, attributes, or relationships.
- Maintaining a long-lived dual-read or dual-write compatibility mode for legacy serialized artifacts.

## Decisions

### Canonical common schema

`entity_id` remains the required immutable primary key. `entity_name`, `desc`, `alias`, and `entity_type` are required common fields; `alias` is always a list of strings. `attributes` is a required object and defaults to `{}` when no type-specific metadata is confirmed. `relationships` is a required list and defaults to `[]` when no confirmed links exist.

This keeps every record structurally uniform and avoids ambiguous omission semantics. Keeping `entity_id` outside the requested descriptive-property list is necessary because both storage layers and relationships require a stable reference. An alternative of using `entity_name` as identity is rejected because names and aliases are mutable and can collide.

### Attributes extension point

`attributes` is a JSON-compatible dictionary with string keys. Values MUST be JSON-safe scalar values, arrays, or nested objects; they MUST NOT contain secrets, runtime connection data, or unbounded raw payloads.

The service does not prescribe entity-type-specific keys in this change. This avoids prematurely freezing a DV ontology while still allowing future specifications to introduce controlled keys. Storing arbitrary top-level fields is rejected because it weakens contract discoverability and API-safe filtering.

### Relationship representation and validation

Each relationship is an object containing `relation_type` and `target_entity_id`, both non-empty strings. `target_entity_id` MUST resolve to an entity in the same loaded structured-entity dataset. Duplicate relationships with the same normalized `(relation_type, target_entity_id)` pair are rejected or deterministically deduplicated; implementation will select one behavior and test it consistently.

The relation is stored on the source entity and is directional. Bidirectional semantics require two explicit records. A relation object with source ID embedded is rejected as redundant, and an untyped list of IDs is rejected because it loses semantic meaning.

### Atomic schema migration

All persisted V3 entity artifacts, Python models, storage validation, catalog conversion, API serializers, frontend adapters, test fixtures, and contract documents migrate in the same change. No runtime fallback reads the legacy field names after migration. This exposes incomplete migrations immediately through fail-closed artifact loading and contract tests.

An adapter-based dual schema reader was considered but rejected: it would extend the legacy contract indefinitely and make it unclear which shape clients should write. Git history provides rollback for this local demo baseline.

### Alias and storage invariants remain unchanged

The Redis entity-word cache continues to derive allowed keys only from `entity_name` and confirmed entries in `alias`. It continues to map a normalized word to exactly one `entity_id`; conflicts or dangling IDs fail closed. `attributes` and `relationships` do not participate in automatic alias creation or matching in this change.

## Risks / Trade-offs

- [Breaking API and fixture contract] → Update all producers and consumers atomically, then enforce absence of legacy names in contract tests.
- [Uncontrolled growth in attributes] → Restrict values to JSON-safe data and preserve safe API projection/redaction; introduce type-specific schemas only in future scoped changes.
- [Dangling or misleading relationships] → Validate targets during structured-store startup and require explicit typed, directional links.
- [Incomplete UI migration] → Add frontend adapter tests and Web API projection tests covering an entity with attributes and relationships.
- [Legacy documentation divergence] → Update the current data contract and relevant V3 guidance as part of the migration tasks.

## Migration Plan

1. Define the canonical models and validation rules.
2. Convert V3 structured-entity artifacts and all supporting fixtures to the canonical keys, including explicit empty extension fields.
3. Update storage, catalog, linking, retrieval, Web/API, and frontend mappings as one repository change.
4. Update contract documentation and test expectations; run full regression plus V3 evaluation and acceptance smoke.
5. Roll back by reverting the implementation commit and its artifact changes together; do not mix old artifacts with new code.

## Open Questions

- The initial accepted vocabulary for `relation_type` is intentionally deferred; this change only requires a non-empty explicit type.
- The initial V3 samples may keep `attributes` and `relationships` empty unless confirmed domain metadata and links are available.
