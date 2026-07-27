import os
import sys
import logging
# sentence_transformers import moved inside __init__ to prevent top-level import MemoryErrors
from sqlalchemy import create_engine, text

# Setup paths
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(RAG_DIR))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.core.database import DATABASE_URL

logger = logging.getLogger("EmbeddingManager")

class MockEncoder:
    """
    Fallback mock encoder when system memory allocation fails.
    Provides consistent mock vector outputs of dimension 384.
    """
    def encode(self, texts: list):
        import numpy as np
        vectors = []
        for text_str in texts:
            char_sum = sum(ord(c) for c in str(text_str))
            np.random.seed(char_sum % 65535)
            vec = np.random.randn(384)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec)
        return np.array(vectors).astype("float32")

class EmbeddingManager:
    """
    Manages SentenceTransformer embedding creations, batch encoding,
    and DB record loading routines for RAG pipelines.
    """
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer loaded: all-MiniLM-L6-v2")
        except (Exception, BaseException) as e:
            logger.warning(f"Failed to load SentenceTransformer: {e}. Falling back to MockEncoder.")
            self.encoder = MockEncoder()

    def get_embedding(self, text_str):
        return self.encoder.encode([text_str])[0]

    def get_embeddings_batch(self, texts_list):
        return self.encoder.encode(texts_list)

    def load_latest_database_records(self):
        """Pulls recent transactions and risk metrics for embedding creation."""
        engine = create_engine(DATABASE_URL)
        records = []
        
        try:
            with engine.connect() as conn:
                # Check if tables exist
                conn.execute(text("SELECT 1 FROM silver_transactions LIMIT 1"))
                
                # Load transactions
                tx_rows = conn.execute(text("SELECT ref_number, platform_name, amount, method, status FROM silver_transactions LIMIT 100")).fetchall()
                for row in tx_rows:
                    content = f"Transaction reference {row[0]} processed {row[2]} INR via {row[3]} on platform {row[1]} with status {row[4]}."
                    records.append({
                        "id": f"tx_{row[0]}",
                        "source": "silver_transactions",
                        "content": content
                    })
                    
                # Load platform risk metrics
                try:
                    platform_rows = conn.execute(text("SELECT platform_name, transaction_count, success_rate, risk_score FROM gold_platform_metrics LIMIT 50")).fetchall()
                    for row in platform_rows:
                        content = f"Platform {row[0]} has processed {row[1]} transactions with a success rate of {row[2]:.2f} and risk score of {row[3]}."
                        records.append({
                            "id": f"platform_{row[0]}",
                            "source": "gold_platform_metrics",
                            "content": content
                        })
                except Exception as pe:
                    logger.warning(f"Could not load gold metrics: {pe}")
        except Exception as e:
            logger.warning(f"Database tables not ready for RAG syncing: {e}")
        finally:
            engine.dispose()
            
        return records
