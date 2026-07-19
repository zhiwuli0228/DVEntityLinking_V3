# Volume x Length x Concurrency x Cold/Warm Matrix Benchmark

- started: 2026-07-18T04:53:04.711195+00:00
- finished: 2026-07-18T05:39:14.386225+00:00
- duration/cell: 10s, warmups: 3
- cold note: FLUSH TABLES el_entity_word, el_entity; approximate (InnoDB buffer pool may retain pages)
- total cells: 256

## Data volumes

| volume | entity_words | entities | data_version |
|---|---|---|---|
| 50k | 50000 | 16667 | mock-vol_50k-50000-20260718041833 |
| 100k | 100000 | 33334 | mock-vol_100k-100000-20260718041841 |
| 200k | 200000 | 66667 | mock-vol_200k-200000-20260718041856 |
| 500k | 500000 | 166667 | mock-vol_500k-500000-20260718041932 |

## 1. Volume scaling (remote_match, warm, c=1, p50 ms)

| volume | short | medium | long | ultra |
|---|---|---|---|---|
| 50k | 47.7 | 47.4 | 65.0 | 47.5 |
| 100k | 40.5 | 60.3 | 97.0 | 96.8 |
| 200k | 97.7 | 89.3 | 98.4 | 88.9 |
| 500k | 70.4 | 79.6 | 98.7 | 99.5 |

## 2. Concurrency scaling (remote_match, warm, 500k, p50 ms)

| concurrency | short | medium | long | ultra |
|---|---|---|---|---|
| 1 | 70.4 | 79.6 | 98.7 | 99.5 |
| 5 | 83.3 | 82.7 | 83.2 | 86.9 |
| 10 | 165.7 | 167.2 | 174.8 | 174.5 |
| 20 | 330.4 | 331.3 | 345.3 | 345.8 |

## 3. Concurrency scaling (remote_match, warm, 500k, QPS)

| concurrency | short | medium | long | ultra |
|---|---|---|---|---|
| 1 | 14.2 | 12.5 | 10.1 | 9.6 |
| 5 | 59.7 | 59.8 | 59.3 | 57.0 |
| 10 | 59.8 | 59.6 | 56.3 | 56.2 |
| 20 | 59.8 | 59.6 | 57.4 | 57.3 |

## 4. Length sensitivity (remote_match, warm, c=1, p50/p95/max ms)

| length (chars) | p50 | p95 | max |
|---|---|---|---|
| short (25) | 47.7 | 48.5 | 63.5 |
| medium (100) | 47.4 | 48.2 | 54.7 |
| long (300) | 65.0 | 65.8 | 66.2 |
| ultra (600) | 47.5 | 48.1 | 53.8 |

## 5. Cold vs warm (remote_match, c=1, medium, p50 ms)

| volume | cold p50 | warm p50 | cold max | warm max | ratio (warm/cold) |
|---|---|---|---|---|---|
| 50k | 47.2 | 47.4 | 49.0 | 54.7 | 1.00 |
| 100k | 60.4 | 60.3 | 61.3 | 61.3 | 1.00 |
| 200k | 88.8 | 89.3 | 111.2 | 95.4 | 1.01 |
| 500k | 80.0 | 79.6 | 93.0 | 82.9 | 1.00 |

## 6. remote_match vs query_recall (warm, c=1, medium, p50 ms)

| volume | remote_match p50 | query_recall p50 | ratio (qr/rm) |
|---|---|---|---|
| 50k | 47.4 | 89.0 | 1.88 |
| 100k | 60.3 | 153.5 | 2.54 |
| 200k | 89.3 | 155.9 | 1.75 |
| 500k | 79.6 | 130.4 | 1.64 |

## Failures: 0/256

