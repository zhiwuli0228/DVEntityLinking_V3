# Volume x Length x Concurrency x Cold/Warm Matrix Benchmark

- started: 2026-07-17T19:38:32.673972+00:00
- finished: 2026-07-17T20:21:04.943894+00:00
- duration/cell: 10s, warmups: 3
- cold note: FLUSH TABLES el_entity_word, el_entity; approximate (InnoDB buffer pool may retain pages)
- total cells: 256

## Data volumes

| volume | entity_words | entities | data_version |
|---|---|---|---|
| 50k | 50000 | 16667 | mock-vol_50k-50000-20260717193752 |
| 100k | 100000 | 33334 | mock-vol_100k-100000-20260717191357 |
| 200k | 200000 | 66667 | mock-vol_200k-200000-20260717191412 |
| 500k | 500000 | 166667 | mock-vol_500k-500000-20260717193830 |

## 1. Volume scaling (remote_match, warm, c=1, p50 ms)

| volume | short | medium | long | ultra |
|---|---|---|---|---|
| 50k | 83.0 | 158.8 | 329.9 | 598.4 |
| 100k | 135.4 | 252.8 | 614.0 | 1146.0 |
| 200k | 210.2 | 490.0 | 1204.7 | 2252.6 |
| 500k | 487.6 | 1154.0 | 2916.0 | 5570.4 |

## 2. Concurrency scaling (remote_match, warm, 500k, p50 ms)

| concurrency | short | medium | long | ultra |
|---|---|---|---|---|
| 1 | 487.6 | 1154.0 | 2916.0 | 5570.4 |
| 5 | 1852.5 | 4945.1 | 13680.8 | 26922.1 |
| 10 | 3691.5 | 10256.6 | 28080.7 | 54370.8 |
| 20 | 7396.5 | 20317.6 | 55698.9 | 113436.9 |

## 3. Concurrency scaling (remote_match, warm, 500k, QPS)

| concurrency | short | medium | long | ultra |
|---|---|---|---|---|
| 1 | 2.0 | 0.9 | 0.3 | 0.2 |
| 5 | 2.6 | 1.0 | 0.4 | 0.2 |
| 10 | 2.6 | 1.0 | 0.4 | 0.2 |
| 20 | 2.6 | 1.0 | 0.4 | 0.2 |

## 4. Length sensitivity (remote_match, warm, c=1, p50/p95/max ms)

| length (chars) | p50 | p95 | max |
|---|---|---|---|
| short (25) | 83.0 | 94.9 | 100.7 |
| medium (100) | 158.8 | 171.3 | 178.4 |
| long (300) | 329.9 | 351.4 | 357.5 |
| ultra (600) | 598.4 | 615.0 | 615.0 |

## 5. Cold vs warm (remote_match, c=1, medium, p50 ms)

| volume | cold p50 | warm p50 | cold max | warm max | ratio (warm/cold) |
|---|---|---|---|---|---|
| 50k | 158.9 | 158.8 | 176.2 | 178.4 | 1.00 |
| 100k | 252.9 | 252.8 | 276.6 | 266.8 | 1.00 |
| 200k | 488.8 | 490.0 | 514.6 | 509.7 | 1.00 |
| 500k | 1172.7 | 1154.0 | 1184.1 | 1172.8 | 0.98 |

## 6. remote_match vs query_recall (warm, c=1, medium, p50 ms)

| volume | remote_match p50 | query_recall p50 | ratio (qr/rm) |
|---|---|---|---|
| 50k | 158.8 | 210.4 | 1.32 |
| 100k | 252.8 | 359.9 | 1.42 |
| 200k | 490.0 | 545.0 | 1.11 |
| 500k | 1154.0 | 1295.9 | 1.12 |

## Failures: 1/256

| volume | length | conc | temp | layer | N | transport_err | correctness_fail | error_codes |
|---|---|---|---|---|---|---|---|---|
| 200k | long | 10 | cold | remote_match | 10 | 1 | 0 | {'transport_error': 1} |
