import os
import json
import sqlite3
import argparse
import urllib.request
import numpy as np
from datetime import datetime

# Setup paths
INGESTION_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(INGESTION_DIR, "local_lakehouse.db")
VECTOR_STORE_DIR = os.path.join(INGESTION_DIR, "vector_store")
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "faiss_index.index")
METADATA_PATH = os.path.join(VECTOR_STORE_DIR, "metadata.json")

def serialize_database_records() -> tuple[list[str], list[dict]]:
    """Reads Silver/Gold tables from SQLite and converts each row to a descriptive text sentence."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run lakehouse_etl.py first.")
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    documents = []
    metadata = []
    
    # 1. Serialize Silver Transactions
    try:
        cursor.execute("SELECT * FROM silver_transactions")
        rows = cursor.fetchall()
        for r in rows:
            doc = (f"Transaction: Reference number {r['ref_number']} for user {r['user_id']} "
                   f"is a {r['type'].lower()} of {r['amount']} INR via {r['method']}. "
                   f"The transaction status is {r['status'].upper()} on {r['datetime']}.")
            documents.append(doc)
            metadata.append({"table": "silver_transactions", "key": r["ref_number"], "text": doc})
    except Exception as e:
        print(f"[WARNING] Could not serialize transactions: {e}")
        
    # 2. Serialize Silver Bets
    try:
        cursor.execute("SELECT * FROM silver_bets")
        rows = cursor.fetchall()
        for r in rows:
            doc = (f"Bet: Bet ID {r['bet_id']} for user {r['user_id']} was placed on event "
                   f"'{r['event_name']}' with a stake of {r['stake']} INR and odds of {r['odds']}. "
                   f"The bet status is {r['status'].upper()} resulting in a profit/loss of {r['profit_loss']} INR "
                   f"settled on {r['settlement_time']}.")
            documents.append(doc)
            metadata.append({"table": "silver_bets", "key": r["bet_id"], "text": doc})
    except Exception as e:
        print(f"[WARNING] Could not serialize bets: {e}")

    # 3. Serialize Gold User Metrics
    try:
        cursor.execute("SELECT * FROM gold_user_metrics")
        rows = cursor.fetchall()
        for r in rows:
            doc = (f"Gold User Analytics: User {r['user_id']} has placed a total of {r['total_bets']} bets "
                   f"with an overall win rate of {r['win_rate']}% and a net Profit/Loss of {r['net_pnl']} INR, "
                   f"yielding an overall Return on Investment (ROI) of {r['roi']}%. Updated on {r['last_updated']}.")
            documents.append(doc)
            metadata.append({"table": "gold_user_metrics", "key": r["user_id"], "text": doc})
    except Exception as e:
        print(f"[WARNING] Could not serialize user metrics: {e}")
        
    # 4. Serialize Gold Payment Channels
    try:
        cursor.execute("SELECT * FROM gold_payment_channels")
        rows = cursor.fetchall()
        for r in rows:
            doc = (f"Gold Payment Channel: Method '{r['method']}' has processed a total of {r['total_transactions']} transactions "
                   f"with an overall success rate of {r['success_rate']}% and a total volume of {r['volume']} INR.")
            documents.append(doc)
            metadata.append({"table": "gold_payment_channels", "key": r["method"], "text": doc})
    except Exception as e:
        print(f"[WARNING] Could not serialize payment channels: {e}")

    conn.close()
    return documents, metadata

def reindex_vector_store():
    """Generates embeddings and builds/saves the FAISS index."""
    print("[INFO] Starting semantic reindexing...")
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"[ERROR] Required indexing libraries not installed: {e}")
        return False
        
    documents, metadata = serialize_database_records()
    if not documents:
        print("[WARNING] No records found in SQLite database to index.")
        return False
        
    print(f"[INFO] Loaded {len(documents)} document sentences from SQLite.")
    
    # Initialize Sentence-Transformers
    print("[INFO] Loading Sentence-Transformer model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Generate embeddings
    print("[INFO] Encoding document embeddings...")
    embeddings = model.encode(documents, show_progress_bar=False)
    embeddings = np.array(embeddings).astype("float32")
    
    # Build FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save index and metadata
    faiss.write_index(index, INDEX_PATH)
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"[INFO] Vector store successfully updated and saved at: {VECTOR_STORE_DIR}")
    return True

def search_vector_store(query: str, k: int = 3) -> list[dict]:
    """Queries the FAISS index and returns the top-k matching documents."""
    if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
        print("[WARNING] Vector index does not exist. Reindexing database first...")
        if not reindex_vector_store():
            return []
            
    import faiss
    from sentence_transformers import SentenceTransformer
    
    # Load index and metadata
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    # Generate query embedding
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_emb = model.encode([query]).astype("float32")
    
    # Query FAISS index
    distances, indices = index.search(query_emb, k)
    
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(metadata) and idx >= 0:
            results.append({
                "score": float(dist),
                "table": metadata[idx]["table"],
                "key": metadata[idx]["key"],
                "text": metadata[idx]["text"]
            })
            
    return results

def query_ollama(prompt: str) -> str:
    """Attempts to query a local running Ollama instance."""
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "llama2",
        "prompt": prompt,
        "stream": False
    }
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode("utf-8"), 
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("response", "").strip()
    except Exception:
        return ""

def query_huggingface_cpu(prompt: str) -> str:
    """Attempts to load a small Flan-T5 model on CPU for local answer generation."""
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        print("[INFO] Loading Google FLAN-T5-Base model on CPU...")
        model_name = "google/flan-t5-base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=150, temperature=0.1, do_sample=False)
        return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    except Exception as e:
        print(f"[INFO] Local HF model unavailable: {e}")
        return ""


def query_fallback_rule_based(query: str, context_records: list[dict]) -> str:
    """A highly intelligent rule-based agent fallback that answers queries directly from context data."""
    print("[INFO] Using rule-based cognitive analyzer fallback...")
    q = query.lower()
    
    # Extract channel success rates
    if "success" in q or "reliability" in q or "payment" in q or "channel" in q:
        metrics = []
        for r in context_records:
            if r["table"] == "gold_payment_channels":
                metrics.append(r["text"])
        if metrics:
            return "Based on the payment channel metrics: " + " ".join(metrics)
            
    # Extract user stats (ROI / PnL)
    if "roi" in q or "pnl" in q or "profit" in q or "win rate" in q or "user" in q or "bet" in q:
        stats = []
        for r in context_records:
            if r["table"] == "gold_user_metrics" or r["table"] == "silver_bets":
                stats.append(r["text"])
        if stats:
            return "According to the user database: " + " ".join(stats[:2])
            
    # Generic fallback: summarize top context records
    summaries = [r["text"] for r in context_records]
    if summaries:
        return "Here are the relevant database records found: " + " ".join(summaries)
        
    return "I could not locate any relevant records in the Lakehouse database to answer your query."

def run_rag_pipeline(query: str) -> dict:
    """Executes the complete retrieval-augmented generation sequence."""
    print(f"\n[QUERY] User: '{query}'")
    
    # 1. Retrieve Context
    results = search_vector_store(query, k=3)
    
    # Format retrieved contexts
    context_str = "\n".join([f"- {r['text']}" for r in results])
    print(f"[RETRIEVAL] Retrieved {len(results)} context documents.")
    
    # 2. Build Prompt
    prompt = f"""You are a Lakehouse Analytics Assistant. Answer the user's query strictly based on the provided context database records. If the context does not contain the answer, state that the data is not available.

Context records:
{context_str}

User Query: {query}
Answer:"""

    # 3. Generate Answer (Ollama -> Transformers -> Fallback)
    answer = query_ollama(prompt)
    if not answer:
        answer = query_huggingface_cpu(prompt)
    if not answer:
        answer = query_fallback_rule_based(query, results)
        
    print(f"[GENERATION] RAG Answer:\n{answer}\n")
    return {
        "query": query,
        "answer": answer,
        "retrieved_context": results
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lakehouse Semantic Search & RAG Orchestrator")
    parser.add_argument("--reindex", action="store_true", help="Sync SQLite data to the vector index")
    parser.add_argument("--query", type=str, help="Run a natural language query against the database")
    args = parser.parse_args()
    
    if args.reindex:
        reindex_vector_store()
    elif args.query:
        run_rag_pipeline(args.query)
    else:
        # Default test query
        reindex_vector_store()
        run_rag_pipeline("Which payment methods have a 100% success rate?")
