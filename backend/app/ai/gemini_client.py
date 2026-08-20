import os
import json
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from backend.app.utils.logger import logger

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.is_configured = bool(self.api_key and len(self.api_key) > 5)
        self.genai_client = None
        self.legacy_model = None
        self._init_client()

    def _init_client(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.is_configured = bool(self.api_key and len(self.api_key) > 5)
        if not self.is_configured:
            logger.info("GEMINI_API_KEY not provided. Intelligent local AI reasoning agent will be active.")
            return

        # 1. Try modern google.genai SDK
        try:
            from google import genai
            self.genai_client = genai.Client(api_key=self.api_key)
            logger.info("Google GenAI client initialized successfully.")
            return
        except Exception as e:
            logger.debug(f"google.genai initialization: {e}")

        # 2. Fallback to google.generativeai SDK
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=self.api_key)
            self.legacy_model = legacy_genai.GenerativeModel("gemini-1.5-flash")
            logger.info("Legacy Google GenerativeAI client initialized successfully.")
            return
        except Exception as e:
            logger.warning(f"Failed to initialize Google Gemini client: {e}. Falling back to local agent.")
            self.is_configured = False

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        # Check if API key was updated at runtime
        current_key = os.getenv("GEMINI_API_KEY", "").strip()
        if current_key and current_key != self.api_key:
            self._init_client()

        if not self.is_configured:
            return ""

        # Try google.genai client
        if self.genai_client:
            try:
                full_prompt = f"System Instruction: {system_instruction}\n\nUser Prompt: {prompt}" if system_instruction else prompt
                response = self.genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
            except Exception as e:
                # Try fallback model name
                try:
                    response = self.genai_client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=full_prompt
                    )
                    if response and hasattr(response, "text") and response.text:
                        return response.text.strip()
                except Exception as ex:
                    logger.warning(f"Google GenAI generate_content error: {ex}. Utilizing fallback reasoning.")

        # Try legacy model
        if self.legacy_model:
            try:
                full_prompt = f"System Instruction: {system_instruction}\n\nUser Prompt: {prompt}" if system_instruction else prompt
                response = self.legacy_model.generate_content(full_prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Legacy Gemini generation error: {e}. Utilizing fallback reasoning.")

        return ""

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[Dict[str, Any]]:
        text_output = self.generate_text(prompt, system_instruction)
        if not text_output:
            return None
        
        # Clean JSON markdown fences
        cleaned = text_output.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"JSON parsing error from Gemini output: {e}. Output was: {cleaned[:100]}")
            # Try regex to extract first JSON object
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return None

gemini_client = GeminiClient()
