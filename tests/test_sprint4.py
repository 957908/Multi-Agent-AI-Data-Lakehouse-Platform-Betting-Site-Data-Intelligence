import sys
from unittest.mock import MagicMock

# Mock sentence_transformers completely to avoid importing torch and hanging on GPU checks
mock_st = MagicMock()
mock_st.SentenceTransformer.side_effect = Exception("Forced offline fallback for unit tests")
sys.modules['sentence_transformers'] = mock_st

import os
import unittest
import json
import tempfile
import shutil
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import backend/API modules
from backend.app.main import app
from ai_services.RAG.vector_store import FAISSVectorStore
from ai_services.RAG.embedding_manager import EmbeddingManager
from ai_services.RAG.lakehouse_rag import SemanticRAGPipeline
from ai_services.agents.lakehouse_agents import CoordinatorAgent

class TestSprint4(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_embedding_manager_mock(self):
        manager = EmbeddingManager()
        # Verify get_embedding yields a numpy array of size 384
        embedding = manager.get_embedding("Test embedding text query")
        self.assertEqual(len(embedding), 384)

    def test_vector_store_persistent_indexing(self):
        # Create vector store in temp directory
        store = FAISSVectorStore(self.temp_dir, dimension=384)
        
        # Verify empty initially
        self.assertEqual(len(store.metadata), 0)
        
        # Add sample data
        vectors = [[0.1] * 384]
        metadata = [{"id": "faq_test_1", "source": "FAQ", "content": "This is test RAG content."}]
        store.add_vectors(vectors, metadata)
        
        # Verify persistence and retrieval
        self.assertEqual(len(store.metadata), 1)
        self.assertEqual(store.index.ntotal, 1)
        
        # Search
        results = store.similarity_search([0.1] * 384, top_k=1, threshold=2.0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["id"], "faq_test_1")

    def test_rag_pipeline_fallbacks(self):
        rag = SemanticRAGPipeline()
        # Query with keyword to trigger fallback answer rules
        res = rag.answer_query("Explain what the Bronze layer does.")
        self.assertIn("Bronze layer", res["answer"])
        self.assertIn("provider_used", res)

    @patch("backend.app.api.endpoints.get_current_user")
    def test_fastapi_endpoints(self, mock_user):
        # Mock security checks
        mock_user.return_value = MagicMock(role="user")
        client = TestClient(app)
        
        # 1. RAG Health Check
        response = client.get("/api/rag/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["healthy"])
        
        # 2. Vector Index Stats
        response = client.get("/api/vector/stats")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["total_vectors"], 0)
        
        # 3. RAG Query POST
        response = client.post("/api/query", json={"query": "Tell me about gold layer aggregates"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("answer", response.json())
        
        # 4. Coordinator Agent Status GET
        response = client.get("/api/agents/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "IDLE")

    def test_coordinator_agent_workflow(self):
        coordinator = CoordinatorAgent()
        
        # Run async function using asyncio loop
        result = asyncio.run(coordinator.execute_workflow())
        self.assertTrue(result["success"])
        self.assertIn("Executive Summary", open(result["report_path_md"], "r", encoding="utf-8").read())

if __name__ == "__main__":
    unittest.main()
