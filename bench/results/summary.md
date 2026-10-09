### List questions (deep page)

| Version | p50 (ms) | p95 (ms) | p99 (ms) | Requests/s | HTTP errors | Checks passed |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 811.3 | 935.4 | 1039.5 | 28 | 0.0% | 100.0% |
| opt-1-indexes | 664.9 | 979.6 | 1065.6 | 33 | 0.0% | 100.0% |
| opt-2-eager-load | 241.8 | 317.8 | 387.2 | 92 | 0.0% | 100.0% |
| opt-3-keyset | 244.9 | 337.7 | 387.5 | 95 | 0.0% | 100.0% |
| opt-4-exam-sampling | 247.8 | 333.2 | 382.2 | 94 | 0.0% | 100.0% |

### List questions (deep page, topic filter)

| Version | p50 (ms) | p95 (ms) | p99 (ms) | Requests/s | HTTP errors | Checks passed |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 671.5 | 1860.0 | 2167.5 | 23 | 0.0% | 100.0% |
| opt-1-indexes | 634.3 | 2028.8 | 2170.2 | 22 | 0.0% | 100.0% |
| opt-2-eager-load | 296.8 | 2039.4 | 2219.6 | 26 | 0.0% | 100.0% |
| opt-3-keyset | 282.9 | 387.1 | 459.6 | 67 | 0.0% | 100.0% |
| opt-4-exam-sampling | 281.3 | 368.5 | 414.8 | 69 | 0.0% | 100.0% |

### Generate exam

| Version | p50 (ms) | p95 (ms) | p99 (ms) | Requests/s | HTTP errors | Checks passed |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 1074.7 | 1426.5 | 1589.8 | 19 | 0.0% | 100.0% |
| opt-1-indexes | 968.5 | 1292.7 | 1443.8 | 21 | 0.0% | 100.0% |
| opt-2-eager-load | 444.6 | 564.4 | 602.5 | 46 | 0.0% | 100.0% |
| opt-3-keyset | 434.4 | 563.0 | 653.3 | 47 | 0.0% | 100.0% |
| opt-4-exam-sampling | 291.7 | 387.3 | 443.1 | 67 | 0.0% | 100.0% |

### Generate exam (topic filter)

| Version | p50 (ms) | p95 (ms) | p99 (ms) | Requests/s | HTTP errors | Checks passed |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 783.7 | 1886.9 | 2435.0 | 22 | 0.0% | 100.0% |
| opt-1-indexes | 1010.0 | 1289.0 | 1446.7 | 21 | 0.0% | 100.0% |
| opt-2-eager-load | 453.3 | 579.3 | 719.1 | 45 | 0.0% | 100.0% |
| opt-3-keyset | 430.2 | 563.1 | 1262.6 | 44 | 0.0% | 100.0% |
| opt-4-exam-sampling | 305.5 | 420.8 | 477.2 | 63 | 0.0% | 100.0% |

