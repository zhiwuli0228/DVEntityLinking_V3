## ADDED Requirements

### Requirement: V4 startup policy is observable
The production factory SHALL require a health-capable Entity Data IR client and SHALL apply `FAIL_FAST` or `DEGRADED` exactly as configured.

#### Scenario: FAIL_FAST service is unavailable
- **WHEN** factory assembly uses `FAIL_FAST` and IR health fails
- **THEN** assembly SHALL fail with a structured configuration/dependency error and SHALL not substitute a local or V3 data client

#### Scenario: DEGRADED service is unavailable
- **WHEN** factory assembly uses `DEGRADED` and IR health fails
- **THEN** assembly SHALL succeed and a linking request requiring data SHALL return `dependency_failed`
