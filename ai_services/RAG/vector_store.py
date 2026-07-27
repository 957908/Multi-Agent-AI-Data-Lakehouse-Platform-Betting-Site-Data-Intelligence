import os
import faiss
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("VectorStore")

class FAISSVectorStore:
    """
    Manages persistent FAISS vector indices, metadata serialization, 
    and similarity lookup functions with corruption checks.
    """
    def __init__(self, index_dir, dimension=384):
        self.index_dir = index_dir
        self.dimension = dimension
        self.index_path = os.path.join(index_dir, "faiss_index.index")
        self.metadata_path = os.path.join(index_dir, "metadata.csv")
        self.index = None
        self.metadata = []
        
        os.makedirs(self.index_dir, exist_ok=True)
        self.load_index()

    def load_index(self):
        """Safely loads FAISS index and metadata. Rebuilds on corruption detection."""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                self.index = faiss.read_index(self.index_path)
                self.metadata = pd.read_csv(self.metadata_path).to_dict(orient="records")
                
                # Check for corruption/mismatch
                if self.index.ntotal != len(self.metadata):
                    logger.warning("FAISS index size mismatch with metadata. Rebuilding.")
                    self.reset_store()
                else:
                    logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors.")
            else:
                self.reset_store()
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}. Rebuilding index.")
            self.reset_store()

    def reset_store(self):
        """Resets/reinitializes empty store."""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        self.save_index()

    def save_index(self):
        """Persists index and metadata to disk."""
        if self.index:
            faiss.write_index(self.index, self.index_path)
        df = pd.DataFrame(self.metadata)
        df.to_csv(self.metadata_path, index=False)

    def add_vectors(self, vectors, metadata_list):
        """Appends new vectors and metadata to store."""
        if len(vectors) != len(metadata_list):
            raise ValueError("Size mismatch between vectors and metadata.")
            
        vectors_np = np.array(vectors).astype("float32")
        self.index.add(vectors_np)
        self.metadata.extend(metadata_list)
        self.save_index()

    def similarity_search(self, query_vector, top_k=3, threshold=1.5):
        """Performs search returning matches within similarity threshold."""
        if self.index is None or self.index.ntotal == 0:
            return []
            
        query_np = np.array([query_vector]).astype("float32")
        distances, indices = self.index.search(query_np, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                dist = float(distances[0][i])
                if dist <= threshold:
                    results.append({
                        "metadata": self.metadata[idx],
                        "distance": dist
                    })
        return results
