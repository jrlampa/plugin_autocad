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
            
        self.model = "mixtral-8x7b-32768" # Good balance of caching/speed

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates a chat response. 
        Context can include current viewport, selected features, or recent errors.
        """
        if not self.client:
            return "AI Service is not configured (missing API key)."

        system_prompt = (
            "You are an expert GIS and AutoCAD assistant named 'sisRUA AI'. "
            "You help users with the sisRUA plugin, explaining how to download OSM data, "
            "generate contours, and export to DXF. "
            "Be concise and technical."
        )

        if context:
            system_prompt += f"\n\nContext: {context}"

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                model=self.model,
                temperature=0.5,
                max_tokens=1024,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return "I'm having trouble connecting to my brain right now. Please try again later."
