# Multi-Agent AI Data Lakehouse Platform - Full Project Report

## 1. Project Overview & Data Flow (Data Kaise Flow Hota Hai)

Hamara project ek end-to-end **Data Lakehouse** aur **AI Intelligence System** hai jo betting sites (jaise 1xBet, 10Cric, 22Bet, Melbet, etc.) ke payment pages aur transaction flows ko scrape, process, analyze aur monitor karta hai.

### Ingestion & Lakehouse Pipeline Workflow:
```
[Betting Sites] ──► [Consolidated Scrapers] ──► [Kafka Brokers (Event Ingestion)]
                                                              │
                                                              ▼
[Lakehouse (MinIO S3 / Iceberg)] ◄── [Spark ETL] ◄── [Flink Stream Cleaning]
           │
           ▼
[FastAPI REST API Server] ──► [PostgreSQL/SQLite DB] ──► [Vite React Dashboard UI]
           │
           ▼
[AI Services (ML Anomaly Sandbox / FAISS RAG Chat / CrewAI Multi-Agents)]
```

---

## 2. File & Folder Connections (Kaun Si File Kahan Connect Hai)

Hamara project **Clean Architecture** follow karta hai. Niche har folder aur file ka connection detail mein diya gaya hai:

### A. Scrapers Folder (`scrapers/`)
* **`scrapers/selenium/`**: Isme standalone Selenium scrapers hain jo manually captcha and login complete hone ke baad cashier (Deposit) page se payments, UPI QR keys, bank accounts, aur crypto addresses nikalte hain.
  * **1xBet**: [1bet_robust_scraper.py](file:///D:/kadam/project/scrapers/selenium/1xbet/1bet_robust_scraper.py)
  * **10Cric**: [automated_scraping.py](file:///D:/kadam/project/scrapers/selenium/10cric/automated_scraping.py)
  * **22Bet**: [payment_scraper.py](file:///D:/kadam/project/scrapers/selenium/22bet/payment_scraper.py)
* **`scrapers/scrapy/`**: Centralized crawling framework. Isme Scrapy Spiders hain (jaise `cric10`, `melbet`, `stake`, `mostbet`, `parimatch`, `bet22`) jo user reviews, complaints aur multiple transaction items ko automatically simulate aur crawl karte hain.

### B. Data Pipelines Folder (`data_pipelines/`)
* **`data_pipelines/kafka/`**: Scrapers se aane wale transaction data ko real-time ingest karta hai.
  * `kafka_producer.py`: Kafka topic pe transaction logs send karta hai.
  * `kafka_consumer.py`: Transactions consume karta hai aur validation fail hone par **Dead Letter Queue (DLQ)** me send karta hai.
* **`data_pipelines/flink/`**: `flink_consumer.py` real-time transaction windowing aggregations aur cleaning handle karta hai.
* **`data_pipelines/spark/`**: Batch processing aur Lakehouse operations handle karta hai.
  * `simulate_bronze.py`: Raw transaction records generate karta hai.
  * `spark_etl.py`: Apache Spark session start karke **Nessie Catalog** and **Apache Iceberg** tables format me data process karke **MinIO** storage pe save karta hai. Agar Spark locally available nahi hai to automatically local SQLite DB fallback execute karta hai.

### C. AI Services Folder (`ai_services/`)
* **`ai_services/ml_models/`**: ML model training aur inference.
  * `train_ml_pipelines.py`: Random Forest (payment router classification), Isolation Forest (anomaly detection), aur K-Means (clustering) train karke joblib format me `registry/` me save karta hai.
* **`ai_services/RAG/`**: Semantic Search.
  * `lakehouse_rag.py`: Database aur log data ko index karke FAISS vector index store banata hai jo chatbot queries ka answer deta hai. Agar system memory short ho (e.g., Windows paging size error 1455) to automatically lightweight `MockEncoder` load karta hai.
* **`ai_services/agents/`**: Cooperative Multi-Agents simulation.
  * `lakehouse_agents.py`: CrewAI pattern ke asyncio agents run karta hai (Scraper, Validator, AnomalyDetector, Reporter) jo background anomalies monitor karte hain aur auto-report `agent_report.md` write karte hain.

### D. Web Application App Layers (`backend/` & `frontend/`)
* **`backend/`**: FastAPI server jo endpoints expose karta hai:
  * `/api/auth/register` & `/api/auth/login`: User register aur login JWT token access key generation.
  * `/api/query`: FAISS vector index se chatbot answers fetch karta hai.
  * `/api/predict-anomaly`: Isolation Forest predict runs.
  * `/api/agents/run`: CrewAI agent loop backend task start.
  * `backend/app/core/database.py`: Self-healing database connection. Agar local PostgreSQL connection verify fail ho jaye (credentials incorrect or offline), to automatically local SQLite `betting_lakehouse.db` connect ho jata hai taaki server bina crash huye boot ho sake.
* **`frontend/`**: Vite + React + TS dashboard client jo port `3000` pe real-time charts, analytics, and query parameters display karta hai.

---

## 3. Phases Completed (Humne Kya-Kya Complete Kar Diya Hai)

Humne project ke saare critical enterprise phases complete kar liye hain:
1. **Clean Architecture Redesign**: Pure workspace ko solid modular layers (`scrapers`, `data_pipelines`, `ai_services`, `backend`, `frontend`) me restructure kar diya hai.
2. **Self-Healing Features**: Database fallback (PostgreSQL -> SQLite) aur memory-safe fallback (SentenceTransformer -> MockEncoder) implement kiya hai taaki local Windows deployment bina kisi crash ke smooth chale.
3. **Comprehensive Scrapers**: Standalone Selenium aur Scrapy framework scrapers ko multiple transactions, reviews aur complaints yield karne ke liye update kar diya hai.
4. **ETL & ML Training**: Local pipeline runs complete ho chuke hain aur ML model binaries save ho chuki hain.
5. **Vite Web Dashboard Hosting**: Frontend to production-ready build compile karke directly **GitHub Pages** pe live deploy kar diya hai:
   👉 **[Live App Link](https://957908.github.io/Multi-Agent-AI-Data-Lakehouse-Platform-Betting-Site-Data-Intelligence/)**
