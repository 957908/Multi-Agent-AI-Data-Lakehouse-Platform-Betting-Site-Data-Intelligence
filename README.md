# 🌟 Multi-Agent AI Data Lakehouse Platform
## Betting Site Data Intelligence & Analytics Console

> [!IMPORTANT]
> **CDAC Final Capstone Project - Clean Architecture Refactoring**  
> Reorganized the platform into Clean Architecture separation of concerns: Frontend, Backend API, Data Ingestion (Scrapy + Playwright), Streaming Pipelines (Kafka + Flink), Storage (Apache Iceberg + Project Nessie + PySpark), ML Models, Semantic RAG Search, and CrewAI Multi-Agent Analytics.

---

## ⚡ Live Console Registry

Access the running modules on your web environment or spin them up locally:

| Component / Service | Environment | Access Link | Status Badge |
| :--- | :---: | :--- | :--- |
| **GitHub Pages Web Console** | **Live Web** | [Live Web Console](https://957908.github.io/Multi-Agent-AI-Data-Lakehouse-Platform-Betting-Site-Data-Intelligence/) | ![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-222222?style=flat-square&logo=github&logoColor=white) |
| **Vite React UI Dashboard** | **Local Dev** | [http://localhost:8085](http://localhost:8085) | ![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB) |
| **FastAPI REST Backend** | **Local API** | [http://localhost:8085/docs](http://localhost:8085/docs) | ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi) |
| **Grafana Metrics Analytics** | **Local Dev** | [http://localhost:3001](http://localhost:3001) | ![Grafana](https://img.shields.io/badge/Grafana-F46800?style=flat-square&logo=grafana&logoColor=white) |
| **MinIO Storage Dashboard** | **Local Dev** | [http://localhost:9001](http://localhost:9001) | ![MinIO](https://img.shields.io/badge/MinIO_S3-C92847?style=flat-square&logo=minio&logoColor=white) |

---

## 🏗️ Unified Data Pipeline & System Flow Diagram

```
[ Scrapy + Playwright Crawlers ] 
             |  (Validates, exports raw JSON logs, rotates User-Agents)
             v  (Falls back to direct PostgreSQL inserts if Kafka is offline)
    [ Kafka Broker (9092) ]
             |
             v  (10s Watermarks event time, filters late arrivals, deduplicates)
   [ Apache Flink Cleaner ]
             |
             v  (Writes partitioned JSON files to Bronze Layer)
[ MinIO S3 Bronze Storage ]  (year=YYYY/month=MM/day=DD/platform=name)
             |
             v  (PySpark Schema Cast, deduplicates transaction reference IDs)
[ Silver Table (Iceberg)  ]  (nessie.silver_transactions version-controlled)
             |
             v  (Aggregates channel volume metrics and platform risk scores)
[ Gold Tables (Iceberg)   ]  (nessie.gold_payment_channels, nessie.gold_platform_metrics)
             |
             v  (Merge staging SQL UPSERT / SQLite INSERT OR REPLACE fallback)
[ Relational Production DB]  (PostgreSQL betting_lakehouse database)
             |
   +---------+---------+
   |                   |
   v                   v
[FAISS Vector Store] [CrewAI Agents]
   |                   |
   v (all-MiniLM-L6-v2)v (Coordinator -> Risk -> Payment -> Health -> Report)
[Semantic RAG Engine]--+
   | (Ollama / Gemini APIs)
   v
[ FastAPI Backend (8085) ] <---> [ React Dashboard ]
```

---

## 📂 Project Directory Structure

The repository has been refactored into modular cleanliness:

* **`scrapers/`**: Consolidated payment cashier crawlers. Includes `selenium/` standalone cashier scripts (1xBet, 10Cric, 22Bet) and the `scrapy/` crawler engine (Cric10, Melbet, Stake, Mostbet, Parimatch, Bet22).
* **`data_pipelines/`**: Ingestion and medallion ETL layers. Contains `kafka/` brokers (consumers, producers with DLQ), `flink/` stream processors (tumbling windows), and `spark/` Iceberg ETL jobs.
* **`ai_services/`**: AI and machine learning layers. Contains `ml_models/` classification and anomaly pipelines, `RAG/` semantic FAISS vector retrieval indexing, and `agents/` CrewAI orchestration loops.
* **`frontend/`**: React + TypeScript + Vite dashboard using Tailwind CSS and Recharts. Packages built static pages served by the backend container.
* **`backend/`**: FastAPI REST API following Repository Pattern, mapping models/schemas and supporting JWT session authentication. Runs on port `8085`.
* **`monitoring/`**: Prometheus config scraping backend diagnostic metrics and routing to Grafana (port `3001`).

---

## 🛠️ Sprint-by-Sprint Implementation Highlights

### 1. Ingestion & Scrapy Pipeline Details (Sprint 1)
* **Ingestion Pipelines**: Yielded items flow through: `DataValidationPipeline` (checks required fields and positive amount limits) $\to$ `JsonExportPipeline` (exports local copies) $\to$ `KafkaPublisherPipeline` (streams transactions to raw Kafka topics) $\to$ `PostgresExportPipeline` (fallback database write block).
* **Broker Online/Offline Fallback**: When Kafka is available, transactions publish to broker streams and set `_pushed_to_kafka = True`. Downstream database writers detect this flag and skip database insertions to avoid duplicate rows. If Kafka is unreachable, direct database insertion executes immediately.

### 2. Real-Time Streaming Ingestion Pipeline (Sprint 2)
* **Kafka Topics**: Includes `transactions-clean` (active clean streams), `dead-letter-queue` (corrupted payloads, late events), and `stream-retry` (with exponential backoffs).
* **Flink Cleaners**: Implements tumbling window aggregations, 10s allowed lateness watermarks, deduplication, and writes partitioned JSON storage files using strict platform sanitization rules to block Path Traversal directory actions.
* **Zero-Dependency Exporter**: Exposes real-time throughput metrics on ports `8001` (Kafka) and `8002` (Flink) using light, zero-dependency python handler threads.

### 3. Medallion Lakehouse & PySpark ETL Pipeline (Sprint 3)
* **Medallion Tables**: PySpark jobs read Bronze partition files, validate schemas, and write to Silver/Gold version-controlled Apache Iceberg tables using the Nessie REST catalog.
* **Spark Performance Tuning**: Configures Adaptive Query Execution (AQE), Dynamic Partition Pruning (DPP), Predicate Pushdowns, and column prunings.
* **PostgreSQL UPSERT Sync**: Merges aggregates into the relational production database using a merge-staging schema:
  `INSERT INTO target SELECT * FROM staging ON CONFLICT (conflict_col) DO UPDATE SET ...`
  (SQLite fallback executes standard `INSERT OR REPLACE` transactions).

### 4. AI Layer & Multi-Agent Orchestration (Sprint 4)
* **Embedding Manager**: Uses SentenceTransformers (`all-MiniLM-L6-v2`) to generate 384-dimensional vector logs, with a CPU/RAM memory-safe `MockEncoder` fallback.
* **Persistent FAISS Vector Store**: Saves index files to disk (`faiss_index.index` and `metadata.csv`) with automatic rebuilds on schema mismatch or corruption detection.
* **Semantic RAG**: Compiles citation-tagged prompt templates, executing provider fallbacks:
  `Ollama (local) -> Gemini (cloud API) -> Static Rule-based Context Summaries`
* **CrewAI Multi-Agent Workflow**: Runs cooperative agent tasks passing structured models:
  `CoordinatorAgent -> RAG Query Context -> RiskAnalysisAgent -> PaymentIntelligenceAgent -> PlatformHealthAgent -> DataQualityAgent -> ReportGeneratorAgent (Outputs md and JSON reports)`

### 5. Production Layer & Deployment (Sprint 5)
* **React Dashboard Refactoring**: Modularizes `App.tsx` layout components (`ErrorBoundary`, `StreamingStatus`, `RAGChat`, `AgentConsole`) and implements `api.ts` REST controllers.
* **FastAPI Improvements**: Exposes health endpoints (`/health` status, `/health/live` liveness, `/health/ready` check DB engine connectivity) and applies security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).
* **CI/CD Pipeline**: GitHub Actions (`ci.yml`) executes flake8 python linter, 22 python test suites, Node React compilation, and multi-stage Docker builds automatically.

---

## 🚀 Getting Started Guide

### Step 1: Install Python and Node Libraries
1. Install Python packages:
   ```powershell
   pip install pandas numpy scikit-learn joblib sentence-transformers faiss-cpu fastapi uvicorn playwright sqlalchemy passlib python-jose email-validator kafka-python pydantic-settings httpx
   playwright install
   ```
2. Install Frontend Node modules:
   ```powershell
   cd frontend
   npm ci
   ```

### Step 2: Spin Up Infrastructure Containers
Use Docker Compose from the root directory to launch databases, event brokers, and dashboards:
```powershell
docker-compose up -d
```
*Verify containers running inside your Docker client console.*

### Step 3: Run Setup & Startup Pipeline
We created a **Unified Setup and Startup Runner script** to make it extremely easy to run and test the entire Data Lakehouse platform. 
Run:
```powershell
python run_project_pipeline.py
```
This script will verify your dependencies, initialize the database schema, simulate ingestion data, run the ETL job, train machine learning classifiers, and help you launch FastAPI, Grafana, and the dashboard with ease.

### Step 4: Execute Test Suite
To verify that all 22 python unit/integration test cases across all Sprints pass successfully:
```powershell
python -m unittest discover -s tests
```

---

## 🔒 Security Hardening Specifications

* **Middlewares**: Attaches unique `X-Request-ID` UUIDs and `X-Process-Time` latencies to API responses.
* **CORS Policy**: Configured to restrict origin requests from unverified client domains.
* **Input Sanitization**: Filters special characters from query strings and limits length.
* **Safe Log Masking**: Automatically strips out access keys, database passwords, and prompt details.

---

## 🛠️ Disaster Recovery & Recovery Procedures

### 1. Database Connection Deadlocks
* **Symptom**: API endpoints hang or return connection timeout errors on SQLAlchemy queries.
* **Recovery**: Clear the connection pool by calling:
  ```python
  from backend.app.core.database import engine
  engine.dispose()
  ```
  Check active transactions in PostgreSQL:
  ```sql
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction';
  ```

### 2. Nessie Catalog Rollbacks
* **Symptom**: Bad ETL ingestion load corrupted the Silver/Gold tables data.
* **Recovery**: Execute Nessie command-line reset to rollback catalog reference branch back to a known clean commit:
  ```bash
  nessie branch --force-reset main branch-commit-hash-before-etl
  ```

### 3. GPU Memory allocation crash (Windows error 1455)
* **Symptom**: PyTorch CUDA loading crashes the RAG engine on system boot.
* **Recovery**: The platform automatically handles this by activating the memory-safe `MockEncoder`. To force it manually, set `LLM_PROVIDER=ollama` or mock the sentence-transformers modules in the env variables.
