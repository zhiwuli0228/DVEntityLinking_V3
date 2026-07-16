## ADDED Requirements

### Requirement: V5 SHALL run an initial entity refresh after service startup
V5 SHALL expose a service lifecycle operation that initiates an entity refresh after startup and exposes whether the initial build is pending, running, succeeded, failed, or skipped.

#### Scenario: Service startup initializes refresh
- **WHEN** the V5 lifecycle is started with entity refresh enabled
- **THEN** it invokes exactly one initial refresh according to the configured blocking/background mode and records its safe outcome.

### Requirement: V5 SHALL schedule one daily midnight refresh per active instance
V5 SHALL schedule a refresh at configured local midnight with an explicit time zone, and SHALL prevent overlapping refresh execution within one process.

#### Scenario: Daily trigger occurs while idle
- **WHEN** the configured midnight trigger occurs and no refresh is running
- **THEN** V5 starts one refresh and records the scheduled trigger.

#### Scenario: Daily trigger overlaps a running refresh
- **WHEN** the configured midnight trigger occurs while a prior refresh is still running
- **THEN** V5 does not start a second refresh and records a safe `refresh_skipped_in_progress` outcome.

### Requirement: Refresh failure SHALL preserve the previous published data snapshot
V5 SHALL retain the prior successful current data snapshot when refresh retrieval, validation, reconciliation, or snapshot switching fails, and SHALL expose a sanitized failure result for observability. A daily refresh SHALL NOT alter the V5 software version.

#### Scenario: Scheduled build fails validation
- **WHEN** a scheduled refresh produces an invalid canonical batch
- **THEN** V5 leaves the prior current data snapshot unchanged and records the validation failure without raw source payload.
