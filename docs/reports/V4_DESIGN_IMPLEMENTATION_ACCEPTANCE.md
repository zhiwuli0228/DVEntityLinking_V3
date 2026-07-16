# V4 Design / Implementation Acceptance Record

Date: 2026-07-16

## Evidence

- `python -m pytest -q` completed successfully: 121 tests passed.
- V4 focused contract suite completed successfully: 32 tests passed.
- Static V4 runtime dependency scan found no V3 Mock, Redis, Gauss JSON, Flask, or direct HTTP adapter dependency in `module.py`, `domain/`, or `entity_data_ir.py`.

## Coverage

| Commitment | Evidence |
| --- | --- |
| Production assembly | Factory requires Entity Data IR URL and platform Client; health policy is black-box tested. |
| Lifecycle | `HEALTH` returns safe status plus data/contract versions; FAIL_FAST and DEGRADED are tested. |
| Domain migration | Intent, recognition, type, candidate, selection, aggregation, and trace components are independently injectable. |
| LLM / async | S3/S5 remain the only hooks; strict S5 failures retain Top-K ambiguity and async offloads synchronous work. |
| IR end-to-end failures | Contract mock covers health, timeout, version mismatch, cross-type ambiguity, and invalid S5 selection. |
| Historical assets | Production factory has no local/mock/HTTP fallback; historical clients remain explicit test wiring only. |
