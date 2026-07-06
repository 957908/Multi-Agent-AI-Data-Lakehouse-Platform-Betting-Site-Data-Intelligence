# Multi-Agent AI Data Lakehouse Platform
## Betting Site Data Intelligence & Analytics Console

This repository implements a fully open-source, high-performance **Multi-Agent AI Data Lakehouse Platform** designed to ingest, process, and analyze dynamic transactional records and game data. 

The project features real-time stream ingestion, a medallion-structured lakehouse architecture (SQLite fallback), classical and anomaly machine learning boundaries, semantic vector search (RAG) using FAISS, and cooperative multi-agent task execution.

---

## 1. System Architecture

```mermaid
graph TD
    subgraph 1. Data Acquisition (Phase 1)
        Melbet[Melbet Playwright Scraper]
        Cric[10Cric Playwright Scraper]
    end
    
    subgraph 2. Ingestion & Streaming (Phase 2)
        Producer1[Melbet Kafka Producer] -->|Topic: melbet-raw-data| Kafka[Apache Kafka Cluster]
        Producer2[10Cric Kafka Producer] -->|Topic: 10cric-raw-data| Kafka
        Kafka -->|Listen & Stream| Consumer[stream_consumer.py]
    end
    
    subgraph 3. Medallion Storage Lakehouse (Phase 3)
        Consumer -->|Write Raw JSON| Bronze[Bronze Directory Layers]
        ETL[lakehouse_etl.py] -->|Read Bronze JSON| Transform[Clean & Type Conversion]
        Transform -->|Write Structured| Silver[Silver SQL Tables]
        Transform -->|Write Aggregated| Gold[Gold SQL Analytics]
    end
    
    subgraph 4. AI & Analytics (Phases 4, 5, 6)
        Silver -->|Features| ML[Random Forest / Isolation Forest / K-Means]
        Gold -->|Text Serialization| Embed[Sentence-Transformers]
        Embed -->|Dense Embeddings| FAISS[FAISS Vector Store]
        FAISS -->|Retrieval Context| RAG[lakehouse_rag.py / FLAN-T5-Base]
        RAG -->|REST API Ports| Web[FastAPI Console Interface]
    end

    subgraph 5. Orchestration (Phase 7)
        Agents[lakehouse_agents.py] -->|Asynchronous Message Queues| Actor[Actor-Inbox Coordination]
    end
```

### Core Pipeline Flow:
1. **Scrapers** navigate dynamically rendered single-page apps (SPAs) using Playwright to extract transactional states.
2. **Kafka Event Brokers** capture and queue raw events to prevent data loss.
3. **Medallion ETL Pipeline** processes the raw events through:
   * **Bronze**: Raw unvalidated JSON payloads.
   * **Silver**: Deduplicated, cleaned, and type-validated relational schemas.
   * **Gold**: Aggregated business and channel reliability metrics.
4. **Machine Learning Models** classify channels (Random Forest), score anomalies (Isolation Forest), and group performance (K-Means).
5. **FAISS Vector Database** embeds and indexes textual logs to serve context-rich inputs to local LLMs (RAG).
6. **Multi-Agent Actor Loop** coordinates background validators and reporting engines asynchronously.

---

## 2. Directory Structure

```
D:\kadam\project\
├── melbet_analytics/          # Scraper & database prototypes for Melbet platform
├── 10cric_analytics/          # Sports & casino scraper scripts for 10Cric platform
├── lakehouse_dashboard/       # Front-end UI (index.html, index.css, app.js)
│     └── assets/              # Abstract 3D graphic assets
├── lakehouse_ingestion/       # Core Data Lakehouse & AI Services
│     ├── bronze/              # Bronze storage directory
│     ├── models/              # Saved ML model joblib binaries
│     ├── vector_store/        # FAISS vector store database files
│     ├── lakehouse_etl.py     # Medallion batch processor (Bronze -> Silver -> Gold)
│     ├── train_models.py      # ML classification and anomaly training
│     ├── lakehouse_rag.py     # FAISS vector index building & RAG query pipelines
│     ├── rag_api.py           # FastAPI REST endpoints (/query, /predict-anomaly)
│     └── lakehouse_agents.py  # Asynchronous actor-inbox multi-agent orchestration
└── .gitignore                 # Exclusion configuration for cache, logs & temp files
```

---

## 3. Installation & Setup Guide

Follow these steps to set up and run the entire platform locally on your computer.

### Step 1: Install Python Libraries
Open your terminal (PowerShell or CMD) and run:
```powershell
pip install pandas numpy scikit-learn joblib sentence-transformers faiss-cpu fastapi uvicorn playwright
playwright install
```

### Step 2: Initialize Database and Populate Test Data
Navigate to the central ingestion directory:
```powershell
cd D:\kadam\project\lakehouse_ingestion\
```
1. **Initialize the schema**:
   ```powershell
   python initialize_lakehouse.py
   ```
2. **Simulate Bronze logs**:
   ```powershell
   python simulate_bronze_data.py
   ```
3. **Execute Medallion ETL (Bronze -> Silver -> Gold)**:
   ```powershell
   python lakehouse_etl.py
   ```
   *Note: This script uses an incremental loading logic to filter duplicates and prevent UNIQUE constraint failures on successive runs.*

### Step 3: Train Machine Learning Models
Train your category classification, anomaly detection, and payment clustering algorithms:
```powershell
python train_models.py
```
*Models are automatically evaluated and written to `lakehouse_ingestion/models/`.*

### Step 4: Sync FAISS Index and Start FastAPI Backend
1. **Generate the dense embeddings and build the index**:
   ```powershell
   python lakehouse_rag.py --reindex
   ```
2. **Launch the REST API server**:
   ```powershell
   python rag_api.py
   ```
   *Leave this terminal running. It hosts backend services on port `8080`.*

### Step 5: Launch the Frontend Web Dashboard Console
Open a new terminal window and run:
```powershell
cd D:\kadam\project\lakehouse_dashboard\
python -m http.server 8000
```
Open your web browser and navigate to: **`http://localhost:8000/`** (or `http://127.0.0.1:8000/`).

Here you can:
* Query the project chatbot guide in the bottom right.
* Type custom questions to run the FAISS RAG model.
* Access the **Interactive ML Inference Sandbox** to test transaction anomaly limits dynamically.

### Step 6: Execute the Multi-Agent Simulation
To run the background coordinated Actor-Inbox messaging loops:
```powershell
cd D:\kadam\project\lakehouse_ingestion\
python lakehouse_agents.py
```
*This writes a clean summary markdown report to `lakehouse_ingestion/agent_report.md`.*
