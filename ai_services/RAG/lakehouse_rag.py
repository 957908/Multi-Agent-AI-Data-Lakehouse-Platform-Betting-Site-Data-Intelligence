import os
import sys
import logging
from datetime import datetime
import httpx

# Setup paths to import backend classes dynamically
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(RAG_DIR))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.core.config import settings
from ai_services.RAG.vector_store import FAISSVectorStore
from ai_services.RAG.embedding_manager import EmbeddingManager

logger = logging.getLogger("LakehouseRAG")

class SemanticRAGPipeline:
    """
    RAG coordination layer performing similarity searches, 
    context ranking, Ollama/Gemini API calls, and citation formats.
    """
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        self.vector_store = FAISSVectorStore(os.path.join(RAG_DIR, "vector_store"))
        
        # Populate initial index if empty
        if len(self.vector_store.metadata) == 0:
            self.bootstrap_faq_index()

    def bootstrap_faq_index(self):
        default_faq = [
            {"id": "faq_1", "source": "FAQ", "content": "The Multi-Agent Lakehouse Platform ingests real-time betting flows via Scrapy + Playwright to monitor payment anomalies."},
            {"id": "faq_2", "source": "FAQ", "content": "Bronze layer stores raw unvalidated JSON payloads directly emitted from scrapy producers."},
            {"id": "faq_3", "source": "FAQ", "content": "Silver layer contains deduplicated, cleaned, and type-validated relational schemas inside PostgreSQL."},
            {"id": "faq_4", "source": "FAQ", "content": "Gold layer aggregates transaction metrics like payment channel success rates and user profit-loss indicators."},
            {"id": "faq_5", "source": "FAQ", "content": "Isolation Forest ML model is configured with a 3% contamination factor to detect extreme transaction amount anomalies."}
        ]
        self.index_records(default_faq)

    def index_records(self, records_list):
        """Indexes new records, filtering out existing IDs to prevent duplication."""
        existing_ids = {item.get("id") for item in self.vector_store.metadata if "id" in item}
        new_records = [r for r in records_list if r.get("id") not in existing_ids]
        
        if not new_records:
            logger.info("No new records to index.")
            return False
            
        texts = [r["content"] for r in new_records]
        embeddings = self.embedding_manager.get_embeddings_batch(texts)
        self.vector_store.add_vectors(embeddings, new_records)
        logger.info(f"Indexed {len(new_records)} new records into FAISS.")
        return True

    def sync_with_database(self):
        """Pulls latest tables records and indexes them dynamically."""
        records = self.embedding_manager.load_latest_database_records()
        return self.index_records(records)

    def retrieve_context(self, query: str, top_k: int = 3, threshold: float = 1.8) -> list:
        query_vector = self.embedding_manager.get_embedding(query)
        results = self.vector_store.similarity_search(query_vector, top_k=top_k, threshold=threshold)
        return [r["metadata"] for r in results]

    def call_ollama(self, prompt: str) -> str:
        """Sends HTTP request to local Ollama API."""
        try:
            url = f"{settings.OLLAMA_HOST}/api/generate"
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
            response = httpx.post(url, json=payload, timeout=3.0)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama execution failed: {e}")
        return ""

    def call_gemini(self, prompt: str) -> str:
        """Sends HTTP request to Google Gemini API endpoints."""
        if not settings.GEMINI_API_KEY:
            return ""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            response = httpx.post(url, json=payload, timeout=3.0)
            if response.status_code == 200:
                candidates = response.json().get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.warning(f"Gemini execution failed: {e}")
        return ""

    def execute_llm_inference(self, prompt: str) -> str:
        """Fallback order: Ollama -> Gemini -> Static query mapper."""
        if settings.LLM_PROVIDER == "ollama":
            res = self.call_ollama(prompt)
            if res:
                return res
            res = self.call_gemini(prompt)
            if res:
                return res
        elif settings.LLM_PROVIDER == "gemini":
            res = self.call_gemini(prompt)
            if res:
                return res
            res = self.call_ollama(prompt)
            if res:
                return res
        return ""

    def answer_query(self, query: str) -> dict:
        start_time = datetime.now().timestamp()
        
        # Retrieve context
        context_snippets = self.retrieve_context(query)
        context_text = "\n".join([f"- [{item.get('source')}] {item.get('content')}" for item in context_snippets])
        
        prompt = f"""
        You are a betting site data intelligence analyst.
        Answer the query using ONLY the context provided below.
        If the context does not contain the answer, say "I do not know based on the Lakehouse metadata."
        Do NOT hallucinate or assume values.

        Context:
        {context_text}

        Query: {query}
        Answer:
        """
        
        # Call LLM
        answer = self.execute_llm_inference(prompt)
        
        # Static fallback rules if LLM is offline (Task 3 & 4 fallback)
        if not answer:
            answer = self.static_fallback_generation(query, context_snippets)
            
        latency = float(datetime.now().timestamp() - start_time)
        logger.info(f"RAG query executed in {latency:.3f}s. Answer size: {len(answer)} chars.")
        
        return {
            "query": query,
            "answer": answer,
            "retrieved_context": context_snippets,
            "latency_seconds": latency,
            "provider_used": settings.LLM_PROVIDER if answer else "static_rules_fallback"
        }

    def static_fallback_generation(self, query: str, context_list: list) -> str:
        q = query.lower()
        if "anomaly" in q or "contamination" in q:
            return "Based on the Lakehouse metadata, the Isolation Forest ML model is configured with a 3% contamination factor to flag payment anomalies."
        elif "bronze" in q:
            return "According to the system documentation, the Bronze layer stores raw unvalidated JSON payloads directly emitted from scrapy producers."
        elif "silver" in q:
            return "The Silver layer database contains deduplicated, cleaned, and type-validated relational schemas inside PostgreSQL."
        elif "gold" in q:
            return "The Gold layer aggregates transaction metrics like payment channel success rates and user profit-loss indicators."
        
        # Generate summary of retrieved context
        if context_list:
            citations = ", ".join([c.get("source") for c in context_list])
            return f"Lakehouse Context Summary (Sources: {citations}):\n" + "\n".join([f"* {c['content']}" for c in context_list])
            
        return "I do not know based on the Lakehouse metadata. No context snippets were found matching this query."

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true", help="Sync vector index with production database.")
    args = parser.parse_args()
    
    rag = SemanticRAGPipeline()
    if args.reindex:
        rag.sync_with_database()
