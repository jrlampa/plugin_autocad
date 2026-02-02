import os
import logging
from typing import Optional, Dict, Any, List
from groq import Groq
from backend.core.utils import cache_key

logger = logging.getLogger(__name__)

class AiService:
    """Service to interact with Groq AI API."""
    
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set. AI features will be disabled/mocked.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
            
        self.model = "llama-3.3-70b-versatile" # Latest supported model

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None, job_id: Optional[str] = None) -> str:
        """
        Generates a chat response. 
        Context can include current viewport, selected features, or recent errors.
        job_id: If provided, fetches the job result and uses it as 'Ground Truth' (RAG).
        """
        if not self.client:
            return "AI Service is not configured (missing API key)."

        system_prompt = (
            "You are an expert GIS and AutoCAD assistant named 'sisRUA AI'. "
            "You help users with the sisRUA plugin.\n"
            "CRITICAL INSTRUCTION: You are an INTERPRETER. Do not calculate physics or data yourself. "
            "If a 'REPORT' or 'Context' provides values, use them as the absolute source of truth."
        )

        # RAG Integration
        if job_id:
            try:
                from backend.services.jobs import get_job
                job = get_job(job_id)
                if job and job.get("result"):
                    import json
                    # Limit result size to avoid token overflow? For now, assume reasonable size project summary
                    # In a real heavy RAG, we would summarize it first.
                    res_str = json.dumps(job["result"], default=str)[:10000] 
                    system_prompt += f"\n\n--- REPORT (Ground Truth) ---\nJob ID: {job_id}\nKind: {job['kind']}\nData: {res_str}\n--- END REPORT ---\n"
                    system_prompt += "User Check: Verify the report data before answering questions about quantities or stress/traction."
            except Exception as e:
                logger.error("rag_fetch_failed", error=str(e), job_id=job_id)

        # Audit Log Context (RAG Lite)
        if context and context.get("fetch_audit_logs"):
            try:
                from backend.core.audit import get_audit_logger
                audit = get_audit_logger()
                # Fetch recent logs (e.g. last 5 actions)
                recent_logs = audit.list_logs(limit=5)
                
                audit_str = ""
                for log in recent_logs:
                    audit_str += f"- [{log['created_at']}] {log['event_type']} on {log['entity_type']} {log['entity_id']}: {log['data']}\n"
                
                system_prompt += f"\n\n--- RECENT ACTIVITY (Audit Logs) ---\n{audit_str}--- END ACTIVITY ---\n"
            except Exception as e:
                logger.error("audit_rag_fetch_failed", error=str(e))

        if context:
            system_prompt += f"\n\nContext: {context}"

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                model=self.model,
                temperature=0.3, # Lower temperature for factual accuracy
                max_tokens=1024,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return "I'm having trouble connecting to my brain right now. Please try again later."
