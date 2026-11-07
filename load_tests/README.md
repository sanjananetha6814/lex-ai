# LexAI Load-Testing Suite

This directory contains the automated performance and scalability load-testing framework for the LexAI platform using [Locust](https://locust.io/).

---

## 1. Installation

Ensure your Python virtual environment is active, then install the development dependencies:

```bash
# Using the virtual environment
./venv/bin/pip install -r requirements-dev.txt

# Or install locust directly
./venv/bin/pip install locust
```

Verify installation:
```bash
./venv/bin/locust --version
```

---

## 2. Starting LexAI Locally

Before running any load tests, start the backend server in a separate terminal:

```bash
# From the project root
./venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Verify the API is reachable:
```bash
curl http://127.0.0.1:8000/
# Expected: {"project":"LexAI API","version":"1.0.0","status":"online","documentation":"/docs"}
```

---

## 3. Running with the Interactive Web UI

To run Locust in interactive mode with real-time charts and metrics:

```bash
./venv/bin/locust -f load_tests/locustfile.py --host http://127.0.0.1:8000
```

1. Open your browser to `http://localhost:8089`.
2. Enter the number of users (e.g., `100`), spawn rate (e.g., `10`), and host (`http://127.0.0.1:8000`).
3. Click **Start swarming**.

---

## 4. Running Headless (Automated CLI)

For repeatable benchmark automation without browser overhead:

```bash
./venv/bin/locust -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 10 \
  --spawn-rate 2 \
  --run-time 30s
```

---

## 5. Concurrency Progression Stages

Run each stage independently to map system capacity and latency degradation:

### Stage 1: 10 Users (Baseline)
```bash
./venv/bin/locust -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 10 \
  --spawn-rate 2 \
  --run-time 1m \
  --csv=results/10_users \
  --html=results/10_users.html
```

### Stage 2: 50 Users (Normal Load)
```bash
./venv/bin/locust -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 50 \
  --spawn-rate 5 \
  --run-time 2m \
  --csv=results/50_users \
  --html=results/50_users.html
```

### Stage 3: 100 Users (Moderate Load)
```bash
./venv/bin/locust -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 2m \
  --csv=results/100_users \
  --html=results/100_users.html
```

### Stage 4: 250 Users (Heavy Load)
```bash
./venv/bin/locust -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 250 \
  --spawn-rate 25 \
  --run-time 3m \
  --csv=results/250_users \
  --html=results/250_users.html
```

### Stage 5: 500 Users (Stress Point)
```bash
./venv/bin/locust -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 500 \
  --spawn-rate 50 \
  --run-time 3m \
  --csv=results/500_users \
  --html=results/500_users.html
```

### Stage 6: 1,000 Users (Target Capacity)
```bash
./venv/bin/locust -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 1000 \
  --spawn-rate 100 \
  --run-time 5m \
  --csv=results/1000_users \
  --html=results/1000_users.html
```

---

## 6. Testing Specific Workloads Independently

Use Locust's `--tags` option to isolate subsystems:

```bash
# Test lawyer directory browsing only
./venv/bin/locust -f load_tests/locustfile.py --host http://127.0.0.1:8000 --tags browse --headless -u 100 -r 10 -t 1m

# Test authentication verification only
./venv/bin/locust -f load_tests/locustfile.py --host http://127.0.0.1:8000 --tags auth --headless -u 50 -r 5 -t 1m

# Test AI chat only (requires LEXAI_ENABLE_AI_TESTS=true)
LEXAI_ENABLE_AI_TESTS=true ./venv/bin/locust -f load_tests/locustfile.py --host http://127.0.0.1:8000 --tags chat --headless -u 20 -r 2 -t 1m
```

---

## 7. Safety Gates & Environment Flags

By default, all tests are **read-only and non-destructive**. To benchmark write or AI operations, enable explicit flags:

| Flag | Default | Description |
| :--- | :--- | :--- |
| `LEXAI_ENABLE_AI_TESTS` | `false` | Enables `/api/chat` and AI clause analysis. Keep false to prevent consuming OpenAI quota. |
| `LEXAI_ENABLE_WRITE_TESTS` | `false` | Enables `/api/consultations` booking. Keep false to prevent synthetic database rows. |
| `LEXAI_ENABLE_DOCUMENT_TESTS` | `false` | Enables `/api/documents/upload`. Uses in-memory minimal PDFs. |

Example enabling write tests:
```bash
LEXAI_ENABLE_WRITE_TESTS=true ./venv/bin/locust -f load_tests/locustfile.py --host http://127.0.0.1:8000 --headless -u 50 -r 5 -t 1m
```

---

## 8. CSV & HTML Report Generation

Locust automatically writes metrics to `results/` when using `--csv` and `--html`:

```bash
./venv/bin/locust -f load_tests/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --users 50 \
  --spawn-rate 5 \
  --run-time 1m \
  --csv=results/run_50 \
  --html=results/report_50.html
```

Generated files:
- `results/report_50.html` (interactive charts, response distributions)
- `results/run_50_stats.csv` (summary requests, failures, median, p95, p99)
- `results/run_50_failures.csv` (error log breakdown)

---

## 9. Interpreting Results (p95, p99 & Latency)

- **Median (p50):** The response time that 50% of users experience.
- **p95:** The response time experienced by 95% of users (5% had worse).
- **p99:** The response time experienced by 99% of users (the worst 1% tail latency).

**Healthy Thresholds:**
- Directory read endpoints (`/api/lawyers`): p95 < 200 ms, p99 < 500 ms.
- Auth endpoints (`/api/auth/login`): p95 < 500 ms (Argon2 hash latency).
- AI Chat endpoints (`/api/chat`): p95 < 3,500 ms (LLM generation latency).

---

## 10. Identifying the Degradation Knee (Breaking Point)

The **degradation knee** is the concurrency stage where:
1. **Response times spike non-linearly** (e.g., p95 doubles from 150 ms to 3,000 ms).
2. **Error rates rise above 0%** (e.g., HTTP 500 database locked, HTTP 504 timeouts).
3. **Throughput (RPS) plateaus** while response time continues to climb.

When this occurs, you have identified the exact limit of your current deployment profile.

