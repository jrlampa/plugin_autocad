
import pytest
import os
from unittest.mock import MagicMock, patch
from backend.services.ai import AiService

class TestAiServiceContext:
    
    @pytest.fixture
    def mock_groq(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key"}):
            with patch("backend.services.ai.Groq") as mock:
                client_instance = mock.return_value
                client_instance.chat.completions.create.return_value.choices = [
                    MagicMock(message=MagicMock(content="Mock Response"))
                ]
                yield mock

    @pytest.fixture
    def mock_audit(self):
        # Patch the SOURCE because it is imported locally
        with patch("backend.core.audit.get_audit_logger") as mock:
            logger_instance = mock.return_value
            logger_instance.list_logs.return_value = [
                {
                    "created_at": "2023-10-27 10:00:00",
                    "event_type": "CREATE",
                    "entity_type": "Project",
                    "entity_id": "P-123",
                    "data": {"name": "Test Project"}
                }
            ]
            yield mock

    def test_generate_response_without_context(self, mock_groq):
        service = AiService()
        response = service.generate_response("Hello")
        
        assert response == "Mock Response"
        
        # Verify prompt does NOT contain Context
        call_args = mock_groq.return_value.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        system_prompt = messages[0]["content"]
        assert "Context:" not in system_prompt

    def test_generate_response_with_audit_flag(self, mock_groq, mock_audit):
        service = AiService()
        context = {"fetch_audit_logs": True, "active_layer": "Wall"}
        
        response = service.generate_response("What happened?", context=context)
        
        # Verify prompt DOES contain Audit Logs
        call_args = mock_groq.return_value.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        system_prompt = messages[0]["content"]
        
        assert "--- RECENT ACTIVITY (Audit Logs) ---" in system_prompt
        assert "CREATE on Project P-123" in system_prompt
        assert "Context: {'fetch_audit_logs': True, 'active_layer': 'Wall'}" in system_prompt

