# Performance report - checkout API (team's report, exam case)

Run: 2 minutes, 0 -> 200 users in 60 s, no think time, one run. Load generator: one CI runner (2 vCPU).

| Label | Samples | Average ms | Errors % |
|---|---|---|---|
| POST /checkout | 11,820 | 420 | 6.1 |
| GET /orders/{id} | 23,504 | 95 | 0.4 |

**Conclusion: PASS** - average response time 420 ms is below the 1,000 ms target.

Raw percentiles (exported, not discussed): POST /checkout p50 180 ms, p90 1,950 ms, p95 9,800 ms, p99 15,000 ms (timeout).
Load generator CPU during the run: 97-100 %.
