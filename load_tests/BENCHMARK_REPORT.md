# LexAI Scalability & Load Testing Report

**Date:** November 2026  
**Test Suite:** Locust (Headless CLI)  
**Profile Under Test:** Read & Authentication Path (`POST /api/auth/login`, `GET /api/auth/me`, `GET /api/lawyers*`)  
**Deployment Profile:** Single-node Uvicorn worker, Default SQLAlchemy `QueuePool` configuration  

---

## 1. Executive Capacity Statement

> **Load-test finding:** LexAI's read/authentication deployment profile passed 10, 50, 100, and 250 concurrent-user tests with 0% failures. At 500 concurrent users, the system experienced severe degradation, with 77.17% request failures and throughput collapsing to 2.41 RPS. Backend logs identified SQLAlchemy `QueuePool` exhaustion (`pool_size=5`, `max_overflow=10`, 15 total connections) followed by 30-second connection checkout timeouts.

---

## 2. Concurrency Progression Summary

| Stage | Users | Spawn Rate | Duration | Requests | Failures | Error Rate | RPS | Median (p50) | p95 | p99 | Result |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 10 | 2/s | 15s | 69 | 0 | 0.00% | 4.68 | 3 ms | 73 ms | 78 ms | ✅ Pass |
| **2** | 50 | 5/s | 2m | 2,461 | 0 | 0.00% | 20.64 | 2 ms | 5 ms | 150 ms | ✅ Pass |
| **3** | 100 | 10/s | 2m | 4,914 | 0 | 0.00% | 41.18 | 2 ms | 10 ms | 290 ms | ✅ Pass |
| **4** | 250 | 25/s | 3m | 18,780 | 0 | 0.00% | 104.69 | 2 ms | 9 ms | 470 ms | ✅ Pass |
| **5** | 500 | 50/s | 3m | 368 | 284 | 77.17% | 2.41 | 31,000 ms | 148,000 ms | 149,000 ms | ❌ **Degradation Knee** |

---

## 3. Analysis of the 500-User Degradation Knee

At 250 concurrent users, the system demonstrated near-linear throughput scaling (**104.69 RPS**, sub-10ms p95, 0 failures). However, at 500 concurrent users, throughput collapsed by 97.7% and failure rate surged to 77.17%.

### The Concrete Failure Mechanism
Backend exception telemetry during the 500-user run confirmed connection pool starvation:

```text
File "sqlalchemy/pool/impl.py", line 165, in _do_get
    raise exc.TimeoutError(
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00
```

1. **Default Pool Ceiling:** The default SQLAlchemy engine configuration allowed a maximum of **15 concurrent connections** (`pool_size=5` + `max_overflow=10`).
2. **Checkout Queue Saturation:** When 500 users attempted concurrent authentication and directory lookups, all 15 connections were immediately checked out.
3. **Checkout Timeouts:** Backlogged requests waited in the connection queue until exceeding the 30.0-second timeout, resulting in **146 HTTP 500 errors** on `/api/auth/login` and **31 HTTP 500 errors** across directory endpoints.
4. **Client Socket Resets:** Lingering unserviced requests eventually reset at the transport layer (`ConnectionResetError: Connection reset by peer`).

---

## 4. Current Capacity Verdict

- **250 Concurrent Users:** ✅ **Proven** for the read/authentication workload under local test conditions.
- **500 Concurrent Users:** ❌ **Fails** in the current deployment configuration due to connection pool limits.
- **1,000 Concurrent Users:** ❌ **Do not claim support.**
- **Other Workloads (AI chat, PDF upload/analysis, consultation writes):** ⏳ Require isolated benchmarking before making claims about overall platform capacity.

---

## 5. Production Architectural Recommendations

Before re-running 500-user and 1,000-user benchmarks:

1. **Production Database Migration:** Migrate from SQLite to managed PostgreSQL.
2. **Coordinated Connection Pool Sizing:** Calculate connection pool parameters based on the formula:
   $$\text{Total DB Connections} = \text{Worker Processes} \times (\text{pool\_size} + \text{max\_overflow}) \le \text{PostgreSQL max\_connections}$$
3. **Process Multi-Threading & Multi-Worker Model:** Run multiple Uvicorn worker processes (e.g., 4–8 workers behind a reverse proxy) to distribute event loop and threadpool capacity.
4. **Independent Workload Benchmarks:** Profile AI statutory chat (`POST /api/chat`) and PDF analysis (`POST /api/documents/{id}/analyze`) separately to measure upstream OpenAI API latency and rate limit boundaries.

