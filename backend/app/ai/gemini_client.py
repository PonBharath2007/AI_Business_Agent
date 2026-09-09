import os
import json
import re
import time
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv
from backend.app.utils.logger import logger

load_dotenv()

# Fast production Gemini models
PRIMARY_MODEL = "gemini-2.0-flash"
FALLBACK_MODEL = "gemini-1.5-flash"

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.is_configured = bool(self.api_key and len(self.api_key) > 5)
        self.genai_client = None
        self.legacy_model = None
        self.active_model_name = PRIMARY_MODEL
        self._init_client()

    def _init_client(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.is_configured = bool(self.api_key and len(self.api_key) > 5)
        if not self.is_configured:
            logger.info("GEMINI_API_KEY not provided. Intelligent local AI reasoning agent will be active.")
            return

        # 1. Modern google.genai SDK
        try:
            from google import genai
            self.genai_client = genai.Client(api_key=self.api_key)
            self.active_model_name = PRIMARY_MODEL
            logger.info(f"Google GenAI client initialized with primary model: {PRIMARY_MODEL}.")
            return
        except Exception as e:
            logger.debug(f"google.genai initialization: {e}")

        # 2. Fallback to legacy google.generativeai SDK
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=self.api_key)
            self.legacy_model = legacy_genai.GenerativeModel(FALLBACK_MODEL)
            self.active_model_name = FALLBACK_MODEL
            logger.info(f"Legacy Google GenerativeAI client initialized with model: {FALLBACK_MODEL}.")
            return
        except Exception as e:
            logger.warning(f"Failed to initialize Google Gemini client: {e}. Falling back to local agent.")
            self.is_configured = False

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_output_tokens: Optional[int] = None
    ) -> str:
        current_key = os.getenv("GEMINI_API_KEY", "").strip()
        if current_key and current_key != self.api_key:
            self._init_client()

        if not self.is_configured:
            return ""

        t0 = time.perf_counter()

        # Try modern google.genai client
        if self.genai_client:
            from google.genai import types
            for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
                try:
                    t_api_start = time.perf_counter()
                    config = types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=max_output_tokens,
                        system_instruction=system_instruction
                    )
                    response = self.genai_client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config
                    )
                    t_api_end = time.perf_counter()

                    if response and hasattr(response, "text") and response.text:
                        total_elapsed = time.perf_counter() - t0
                        logger.info(
                            f"[AI Performance] Text generation | model={model_name} | "
                            f"api_call={t_api_end - t_api_start:.2f}s | total={total_elapsed:.2f}s"
                        )
                        return response.text.strip()
                except Exception as ex:
                    logger.warning(f"Google GenAI generate_content error on {model_name}: {ex}")
                    continue

        # Try legacy model
        if self.legacy_model:
            try:
                t_api_start = time.perf_counter()
                full_prompt = f"System Instruction: {system_instruction}\n\nUser Prompt: {prompt}" if system_instruction else prompt
                response = self.legacy_model.generate_content(
                    full_prompt,
                    generation_config={"temperature": 0.3, "max_output_tokens": max_output_tokens} if max_output_tokens else {"temperature": 0.3}
                )
                t_api_end = time.perf_counter()
                if response and response.text:
                    total_elapsed = time.perf_counter() - t0
                    logger.info(
                        f"[AI Performance] Legacy text generation | "
                        f"api_call={t_api_end - t_api_start:.2f}s | total={total_elapsed:.2f}s"
                    )
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Legacy Gemini generation error: {e}. Utilizing fallback reasoning.")

        return ""

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_output_tokens: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        current_key = os.getenv("GEMINI_API_KEY", "").strip()
        if current_key and current_key != self.api_key:
            self._init_client()

        if not self.is_configured:
            return None

        t0 = time.perf_counter()

        # Modern google.genai native JSON generation
        if self.genai_client:
            from google.genai import types
            for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
                try:
                    t_api_start = time.perf_counter()
                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                        max_output_tokens=max_output_tokens,
                        system_instruction=system_instruction
                    )
                    response = self.genai_client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config
                    )
                    t_api_end = time.perf_counter()

                    if response and hasattr(response, "text") and response.text:
                        raw = response.text.strip()
                        parsed = json.loads(raw)
                        total_elapsed = time.perf_counter() - t0
                        logger.info(
                            f"[AI Performance] JSON generation | model={model_name} | "
                            f"api_call={t_api_end - t_api_start:.2f}s | total={total_elapsed:.2f}s"
                        )
                        return parsed
                except Exception as ex:
                    logger.warning(f"Google GenAI JSON generation error on {model_name}: {ex}")
                    continue

        # Fallback to standard text generation + JSON parser
        text_output = self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens
        )
        if not text_output:
            return None

        cleaned = text_output.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"JSON parsing error from Gemini output: {e}. Output snippet: {cleaned[:100]}")
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return None

gemini_client = GeminiClient()
