## 1. Canonical model and validation

- [x] 1.1 Replace legacy entity record fields with `entity_name`, `desc`, `alias`, `attributes`, and `relationships`, while retaining `entity_id` and `entity_type`.
- [x] 1.2 Add validation for required common fields, JSON-compatible attributes, and typed relationship objects.
- [x] 1.3 Enforce fail-closed validation for dangling relationship targets and invalid relationship data.

## 2. Storage and linking migration

- [x] 2.1 Migrate the V3 Gauss Mock artifact and fixtures to the canonical entity field names with explicit attributes and relationships.
- [x] 2.2 Update the Redis Mock, catalog adapter, and linking pipeline to validate entity words against `entity_name` and confirmed `alias` values.
- [x] 2.3 Update retrieval and service-layer conversions to preserve canonical entity records and their extension fields.

## 3. API and frontend migration

- [x] 3.1 Update safe Web/API entity serialization to expose canonical names, permitted attributes, and typed relationships without legacy keys.
- [x] 3.2 Update frontend API adapters, state, and entity-detail rendering for the canonical schema.
- [x] 3.3 Add or revise frontend and Web API tests for canonical fields, safe attribute filtering, and relationship projection.

## 4. Contract, fixtures, and verification

- [x] 4.1 Update the current data contract, V3 design references, sample documentation, and API examples to use the canonical schema.
- [x] 4.2 Migrate all Python test fixtures, golden datasets, and contract assertions; add negative tests for legacy-only records and dangling relationships.
- [x] 4.3 Run the full test suite, V3 evaluation, and V3 acceptance smoke; confirm no public contract emits `canonical_name`, `description`, or `aliases`.
