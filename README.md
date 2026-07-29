# 🌟 SentinelX Betting Intelligence Platform (v2.0)
## Multi-Agent AI Data Lakehouse & Payment Security Console

> [!IMPORTANT]
> **CDAC Final Capstone Project - Clean Architecture & Enterprise Hardening**  
> Reorganized the platform into Clean Architecture separation of concerns: Frontend, Backend API, Data Ingestion (Scrapy + Playwright), Streaming Pipelines (Kafka + Flink), Storage (Apache Iceberg + Project Nessie + PySpark), ML Models, Semantic RAG Search, Multi-Agent Analytics, and Enterprise Monitoring.

---

## ⚡ Live Console Registry

Access the running modules on your web environment or spin them up locally:

| Component / Service | Environment | Access Link | Status Badge |
| :--- | :---: | :--- | :--- |
| **GitHub Pages Web Console** | **Live Web** | [Live Web Console](https://957908.github.io/Multi-Agent-AI-Data-Lakehouse-Platform-Betting-Site-Data-Intelligence/) | ![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-222222?style=flat-square&logo=github&logoColor=white) |
| **Vite React UI Dashboard** | **Local Dev** | [http://localhost:8085](http://localhost:8085) | ![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB) |
| **FastAPI REST Backend** | **Local API** | [http://localhost:8085/docs](http://localhost:8085/docs) | ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi) |
| **Uptime Kuma Alerts** | **Local Dev** | [http://localhost:3002](http://localhost:3002) | ![Uptime Kuma](https://img.shields.io/badge/Uptime_Kuma-3F6 font-square?style=flat-square&logo=uptime-kuma&logoColor=white) |
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
   | (Ollama / Gemini APIs with Term-Overlap NLP verification)
   v
[ FastAPI Backend (8085) ] <---> [ React Dashboard ]
```

---

## 📂 Project Directory Structure

* **`scrapers/`**: Consolidated crawlers. Includes `selenium/` standalone cashier scripts and `scrapy/` crawler engine (Cric10, Melbet, Stake, Mostbet, Parimatch, Bet22). Added `scheduler.py` (APScheduler) for scheduling.
* **`data_pipelines/`**: Ingestion and medallion ETL layers. Contains `kafka/` brokers (consumers, producers with DLQ) and `flink/` stream processors (tumbling windows).
* **`ai_services/`**: AI and machine learning layers. Contains `ml_models/` classification/anomaly pipelines, `RAG/` semantic FAISS vector retrieval indexing, and `agents/` multi-agent orchestrator loops.
* **`frontend/`**: React + TypeScript + Vite dashboard using Tailwind CSS and Recharts. Includes custom knowledge graphs and agent status shells.
* **`monitoring/`**: Prometheus scraping configs, Grafana dashboards, and alert rules.

---

## 🛠️ Sprint-by-Sprint Implementation Highlights

### 1. Ingestion & Scrapy Pipeline Details (Sprint 1)
* **Ingestion Pipelines**: Yielded items flow through: `DataValidationPipeline` $\to$ `JsonExportPipeline` $\to$ `KafkaPublisherPipeline` $\to$ `PostgresExportPipeline` (fallback database write block).
* **Broker Online/Offline Fallback**: Direct database insertion executes immediately if Kafka is unreachable to guarantee zero data loss.
* **Ingestion Scheduler**: Implemented a standalone Python execution manager (`scrapers/scheduler.py`) to run crawlers on clean time intervals.

### 2. Real-Time Streaming Ingestion Pipeline (Sprint 2)
* **Kafka Topics**: Standardized under `sentinelx.raw.*` (input) and `sentinelx.clean.*` (output) topics to handle transactional and metadata flows cleanly.
* **Flink Cleaners**: Implements tumbling window aggregations, 10s watermarks, deduplication, and writes partitioned JSON storage files using strict platform sanitization rules.

### 3. Medallion Lakehouse & PySpark ETL Pipeline (Sprint 3)
* **Medallion Tables**: PySpark jobs read Bronze partition files, validate schemas, and write to Silver/Gold Iceberg tables.
* **Hybrid Processing Fallback**: Automatically invokes a local Pandas-based processor (`run_pandas_fallback_etl`) if JVM/Hadoop or Spark session cannot initialize, keeping local dev operational.

### 4. Machine Learning & Analytics (Sprint 4)
* **Random Forest Classifier**: Classifies payment channels into card, UPI, bank transfer, crypto, or e-wallet routes.
* **Isolation Forest Anomaly Detector**: Flags unusual payment details and amount ranges (configured with 3% expected contamination).
* **MLflow Tracking**: Versioned model properties and hyperparameters are outputted to `mlflow_run.json`.

### 5. Vector Search & RAG Optimization (Sprint 5)
* **FAISS Vector Index**: Maps database records to dense 384-dimensional space using HuggingFace's `all-MiniLM-L6-v2`.
* **NLP Verification Layer**: Added post-processing validation (`verify_answer_overlap`) checking term-overlap between LLM generated answers and FAISS context records to enforce accuracy and highlight unverified facts.

### 6. Deployment & Monitoring (Sprint 6)
* **Docker Orchestration**: Unified `docker-compose.yml` launches databases, Nessie catalog servers, MinIO console dashboards, and monitoring tools.
* **Prometheus Alerting**: Added `alert.rules.yml` to trigger critical alerts on pipeline offline states, high error rates, or excessive duplicate flags.
* **Uptime Kuma**: Deployed Uptime Kuma container on port `3002` to monitor backend service pings and configure notification hooks.

---

## 🚀 Getting Started Guide

### Step 1: Install Python and Node Libraries
```powershell
pip install pandas numpy scikit-learn joblib sentence-transformers faiss-cpu fastapi uvicorn playwright sqlalchemy passlib python-jose email-validator kafka-python pydantic-settings httpx apscheduler
playwright install
```

### Step 2: Spin Up Infrastructure Containers
```powershell
docker-compose up -d
```

### Step 3: Run Setup & Startup Pipeline
```powershell
python run_project_pipeline.py
```
This script will verify your dependencies, initialize the database schema, simulate ingestion data, run the ETL job, train machine learning classifiers, and help you launch backend servers with ease.

### Step 4: Execute Test Suite
```powershell
python -m unittest discover -s tests
```

---

## 🔒 Security Hardening Specifications
* **Middlewares**: Attaches unique `X-Request-ID` UUIDs and `X-Process-Time` latencies to API responses.
* **CORS Policy**: Configured to restrict origin requests from unverified client domains.
* **Safe Log Masking**: Automatically strips out access keys, database passwords, and prompt details.
