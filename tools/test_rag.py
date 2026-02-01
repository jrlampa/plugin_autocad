import os
import sys
import time
import unittest
from pathlib import Path

# Fix path
sys.path.append(os.path.abspath("src/backend"))

from backend.services.ai import AiService
from backend.services.jobs import job_store, init_job, update_job
from backend.core.bus import InMemoryEventBus

class TestLocalRAG(unittest.TestCase):
    def setUp(self):
        # Ensure API Key is available (it should be from environment)
        if not os.environ.get("GROQ_API_KEY"):
            print("WARNING: GROQ_API_KEY not found. Skipping real API call.")
            self.skipTest("No API Key")
            
        self.ai = AiService()
        self.bus = InMemoryEventBus()

    def test_interpretation_of_report(self):
        print("--- Testing RAG Interpretation ---")
        
        # 1. Create a Fake Deterministic Job
        job_id = init_job("traction_simulation")
        
        # 2. Populate it with "Ground Truth" data
        fake_result = {
            "max_tension_dan": 1234.56,
            "critical_pole_id": "POSTE-99",
            "safety_factor": 1.2
        }
        
        update_job(job_id, self.bus, status="completed", result=fake_result)
        
        # 3. Ask AI about it
        query = "Qual é a tração máxima calculada e qual poste é crítico?"
        print(f"Query: {query}")
        
        response = self.ai.generate_response(query, job_id=job_id)
        
        print(f"AI Response:\n{response}")
        
        # 4. Assertions (heuristic)
        self.assertIn("1234.56", response)
        self.assertIn("POSTE-99", response)
        print("[PASS] AI successfully retrieved values from the report.")

if __name__ == "__main__":
    unittest.main()
