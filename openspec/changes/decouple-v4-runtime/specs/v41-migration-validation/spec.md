## ADDED Requirements

### Requirement: Canonical entity migration SHALL validate before publication
V4.1 SHALL provide a dry-run-first migration validator that accepts canonical entity records and verifies required fields, alias-derived words, active normalized-key uniqueness, relationship targets, and safe report generation before any external publication is attempted.

#### Scenario: Valid canonical entities are validated
- **WHEN** canonical entities with valid aliases and relationships are supplied in dry-run mode
- **THEN** the tool returns a deterministic publication bundle and sanitized summary report.

#### Scenario: Conflicting active entity words are supplied
- **WHEN** two active entities derive the same normalized entity word
- **THEN** validation fails closed and no publication bundle is returned.

### Requirement: Deprecated runtime configuration SHALL be rejected
V4.1 configuration validation SHALL identify deprecated V3 Mock, Redis/Gauss, historical catalog, and implicit Flask-runtime settings and reject them for production use.

#### Scenario: Deprecated configuration is supplied
- **WHEN** a configuration contains a prohibited historical runtime key
- **THEN** validation reports the key and rejects the production configuration.
