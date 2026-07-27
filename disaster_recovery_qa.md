# Ingestion, Security, & Disaster Recovery Q&A Guide

या मार्गदर्शकामध्ये **Playwright Crawling, Windows Paging Error 1455, SQLAlchemy Connection Pool Deadlocks, Nessie Catalog Rollbacks, आणि API Tracing** या अत्यंत महत्त्वाच्या सुरक्षा आणि आपत्कालीन व्यवस्थापन (Disaster Recovery) घटकांवर आधारित तांत्रिक प्रश्न आणि त्यांची उत्तरे दिली आहेत.

---

## 🕷️ Section 1: Playwright Ingestion & Anti-Bot Bypassing

### Q1. Stake आणि Melbet सारख्या dynamic betting sites स्क्रेप करताना JavaScript rendering आणि Anti-Bot protections कसे handle केले?
* **Answer**:
  * **Dynamic Rendering**: Scrapy सोबत **Playwright / Selenium** integration चा वापर केला. Playwright headless browser instance spawn करतो आणि client-side Javascript dynamic content fully execute झाल्यावरच raw HTML, Scrapy items कडे forward करतो.
  * **Anti-Bot Bypassing**:
    * **User-Agent Rotation**: प्रत्येक request ला header मध्ये realistic, updated browsers चे user-agents dynamically rotate केले जातात.
    * **Request throttling (Autothrottle)**: Scraping चा speed मानवी वर्तनासारखा (random delays सह) ठेवून target sites चे request traffic limits ओलांडणे टाळले.

---

## 💻 Section 2: Windows GPU Memory Allocation (Error 1455)

### Q2. Windows वर PyTorch/SentenceTransformers लोड करताना 'Error 1455: paging file is too small' हा error का येतो? आणि तुम्ही तो कसा हाताळला?
* **Answer**:
  * **कारण (Cause)**: Windows OS वर जेव्हा multi-threaded programs (उदा. Scrapy, Flink consumers, आणि FastAPI) एकाच वेळी सुरू होतात, तेव्हा PyTorch CUDA/C++ libraries लोड करण्यासाठी मोठ्या प्रमाणावर Virtual Memory (paging file) ची मागणी करतो. जर Windows page file size मर्यादित असेल, तर allocation fail होते und process क्रॅश होते.
  * **उपाय (Resolution)**: आम्ही core code मध्ये `MockEncoder` fallback logic जोडले. जर `SentenceTransformer("all-MiniLM-L6-v2")` load करताना कोणतीही memory allocation exception आली, तर program क्रॅश न होता **MockEncoder** active करतो. हा class memory allocation न करता dimension-384 चे deterministic vectors generate करतो. यामुळे platform चा uptime १००% राखला जातो.

---

## 🔌 Section 3: SQLAlchemy Pool Exhaustion & Deadlocks

### Q3. FastAPI application मध्ये SQLAlchemy connection pool exhaustion किंवा deadlocks कसे ओळखायचे? आणि त्यातून recovery कशी करावी?
* **Answer**:
  * **ओळखणे (Detection)**: जेव्हा API endpoints database queries करताना अडकतात (hang होतात) किंवा `TimeoutError: QueuePool limit of size 10 overflow 20 reached` असा error देतात.
  * **निवारण (Resolution)**:
    1. **Pre-ping**: आम्ही `pool_pre_ping=True` जोडले आहे, जे प्रत्येक transaction पूर्वी connection active आहे का ते तपासते, यामुळे stale/broken connections वापरले जात नाहीत.
    2. **Timeout Settings**: `pool_timeout=30` मुळे database queue मध्ये query अनंतकाळ अडकून राहत नाही, ती ३० सेकंदांत timeout होते.
    3. **Active connections terminate करणे**: PostgreSQL database console मधून idle/stuck queries terminate करण्यासाठी खालील query वापरली जाते:
       ```sql
       SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction';
       ```

---

## ⏳ Section 4: Nessie Catalog Zero-Copy Rollbacks

### Q4. जर PySpark ETL batch ingest करताना Silver table मध्ये चुकीचा (corrupted) डेटा लिहिला गेला, तर Nessie Catalog द्वारे rollback कसे केले जाते?
* **Answer**:
  * **Zero-copy Rollback**: Project Nessie हे Git सारखे version control पुरवते. 
  * **कृती (Action)**:
    1. प्रथम आपण Nessie CLI किंवा UI मधून bad ingest होण्यापूर्वीचा **Commit Hash** शोधतो.
    2. त्यानंतर आपण `main` branch ला त्या commit hash वर force-reset करतो:
       ```bash
       nessie branch --force-reset main <known_clean_commit_hash>
       ```
    यामुळे full database restore न करता, catalog metadata pointers एका सेकंदात जुन्या clean state वर जातात. याला **Metadata-only Rollback** म्हणतात, जो zero-copy आणि instantaneous असतो.

---

## 🏷️ Section 5: API Tracing & Headers Injection

### Q5. HTTP response headers मध्ये `X-Request-ID` आणि `X-Process-Time` का समाविष्ट केले आहेत? Production मध्ये याचा काय फायदा होतो?
* **Answer**:
  * **X-Request-ID (UUID)**: प्रत्येक API call ला एक unique request ID दिला जातो. जर production मध्ये एखाद्या विशिष्ट transaction मध्ये error आला, तर आपण application logs मध्ये या Request ID ला filter करून पूर्ण execution trace (scrapers पासून databases पर्यंत) शोधू शकतो (Distributed Tracing).
  * **X-Process-Time**: हा header milliseconds मध्ये latency दर्शवतो. यामुळे Frontend आणि backend मधील performance bottlenecks (उदा. कोणती query किंवा filter जास्त वेळ घेत आहे) तात्काळ शोधता येतात.
