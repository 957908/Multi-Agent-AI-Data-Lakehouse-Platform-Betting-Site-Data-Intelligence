import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock sentence_transformers completely to avoid importing torch and hanging on GPU checks
sys.modules['sentence_transformers'] = MagicMock()
mock_st = MagicMock()
mock_st.SentenceTransformer.side_effect = Exception("Forced offline fallback for unit tests")
sys.modules['sentence_transformers'] = mock_st

from backend.app.main import app

class TestSprint5(unittest.TestCase):
    def test_health_endpoints(self):
        client = TestClient(app)
        
        # 1. Base Health
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")
        
        # 2. Liveness Check
        res = client.get("/health/live")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "alive")

    def test_middleware_and_headers(self):
        client = TestClient(app)
        res = client.get("/health")
        
        # Check custom middleware headers
        self.assertIn("X-Request-ID", res.headers)
        self.assertIn("X-Process-Time", res.headers)
        
        # Check security hardening headers
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-XSS-Protection"), "1; mode=block")

    @patch("backend.app.main.engine.connect")
    def test_readiness_healthy(self, mock_connect):
        # Mock database connection as successful
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        client = TestClient(app)
        res = client.get("/health/ready")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ready")

    @patch("backend.app.main.engine.connect", side_effect=Exception("Connection timed out"))
    def test_readiness_unhealthy(self, mock_connect):
        client = TestClient(app)
        res = client.get("/health/ready")
        self.assertEqual(res.json()["status"], "unready")

if __name__ == "__main__":
    unittest.main()
