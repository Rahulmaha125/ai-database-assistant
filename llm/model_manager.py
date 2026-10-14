"""Local LLM model management supporting Ollama, Hugging Face, and safe unavailable-model fallback."""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    DEFAULT_GROQ_MODEL,
    DEFAULT_HF_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    GROQ_API_KEY,
    GROQ_API_URL,
    SUPPORTED_GROQ_MODELS,
    SQL_MAX_NEW_TOKENS,
    SQL_TEMPERATURE,
)
from db.init_db import DEMO_QUESTIONS
from llm.sql_generator import SQLGenerator, extract_sql_from_response


class ModelProvider(str, Enum):
    AUTO = "auto"
    GROQ = "groq"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    TEMPLATE_FALLBACK = "template_fallback"


@dataclass
class LLMStatus:
    is_available: bool
    provider: str
    model_name: str
    details: str
    installed_models: List[str] = field(default_factory=list)
    hardware_warning: Optional[str] = None


class LLMManager:
    """Manages cloud (Groq) and local (Ollama/HuggingFace) model inference connections and fallback behaviors."""

    def __init__(
        self,
        provider: str = DEFAULT_LLM_PROVIDER,
        groq_api_key: Optional[str] = None,
        groq_model: str = DEFAULT_GROQ_MODEL,
        groq_api_url: str = GROQ_API_URL,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = DEFAULT_OLLAMA_MODEL,
        hf_model: str = DEFAULT_HF_MODEL,
    ):
        self.provider = provider
        self.groq_api_key = groq_api_key if groq_api_key is not None else GROQ_API_KEY
        self.groq_model = groq_model
        self.groq_api_url = groq_api_url.rstrip("/")
        self.ollama_url = ollama_url.rstrip("/")
        self.ollama_model = ollama_model
        self.hf_model = hf_model
        self._hf_pipeline = None
        self._hf_loaded = False
        self._last_status_time = 0.0
        self._cached_status = None


    def check_groq(self, timeout: float = 3.0) -> tuple[bool, List[str], str]:
        """Check if Groq Cloud API is configured and reachable."""
        if not self.groq_api_key:
            return False, [], "No Groq API key configured."
        try:
            resp = requests.get(
                f"{self.groq_api_url}/models",
                headers={"Authorization": f"Bearer {self.groq_api_key}"},
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                return True, models, "Groq Cloud API connected successfully."
            elif resp.status_code == 401:
                return False, [], "Invalid Groq API key."
            else:
                return False, [], f"Groq API returned HTTP {resp.status_code}."
        except Exception as e:
            return False, [], f"Cannot reach Groq API: {str(e)}"

    def check_ollama(self, timeout: float = 2.0) -> tuple[bool, List[str]]:
        """Check if local Ollama daemon is reachable and list installed models."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return True, models
        except Exception:
            pass
        return False, []

    def check_transformers_installed(self) -> bool:
        """Check if torch and transformers packages are installed."""
        try:
            import torch
            import transformers
            return True
        except (ImportError, OSError, Exception):
            return False

    def get_status(self, force_refresh: bool = False) -> LLMStatus:
        """Inspect environment and return current LLM availability."""
        now = time.time()
        if not force_refresh and self._cached_status is not None and (now - self._last_status_time < 3.0):
            return self._cached_status

        # 1. Check Groq Cloud if configured and provider allows it
        if self.provider in ("auto", "groq") and self.groq_api_key:
            groq_online, groq_models, groq_msg = self.check_groq()
            if groq_online:
                selected_model = self.groq_model if self.groq_model in groq_models else (groq_models[0] if groq_models else self.groq_model)
                status = LLMStatus(
                    is_available=True,
                    provider="groq",
                    model_name=selected_model,
                    details=f"Connected to Groq Cloud API (Ultra-fast). Active model: {selected_model}.",
                    installed_models=groq_models,
                )
                self._cached_status = status
                self._last_status_time = now
                return status
            elif self.provider == "groq":
                return LLMStatus(
                    is_available=False,
                    provider="groq",
                    model_name=self.groq_model,
                    details=f"Groq Cloud connection failed: {groq_msg}",
                    installed_models=[],
                )

        # 2. Check local Ollama daemon
        if self.provider in ("auto", "ollama"):
            ollama_online, ollama_models = self.check_ollama()
            if ollama_online:
                # Prefer configured model, then exact match, then prefix match (e.g. qwen2.5-coder:1.5b)
                matched_model = None
                for m in ollama_models:
                    if m == self.ollama_model or m.startswith(self.ollama_model.split(":")[0]):
                        matched_model = m
                        break
                selected_model = matched_model or (ollama_models[0] if ollama_models else self.ollama_model)
                status = LLMStatus(
                    is_available=True,
                    provider="ollama",
                    model_name=selected_model,
                    details=f"Connected to local Ollama daemon at {self.ollama_url}. Installed models: {', '.join(ollama_models)}.",
                    installed_models=ollama_models,
                )
                self._cached_status = status
                self._last_status_time = now
                return status
            elif self.provider == "ollama":
                return LLMStatus(
                    is_available=False,
                    provider="ollama",
                    model_name=self.ollama_model,
                    details=f"Local Ollama daemon unreachable at {self.ollama_url}.",
                    installed_models=[],
                )

        # 3. Check Transformers pipeline
        if self._hf_loaded and self._hf_pipeline is not None:
            return LLMStatus(
                is_available=True,
                provider="huggingface",
                model_name=self.hf_model,
                details=f"In-memory Hugging Face pipeline loaded: {self.hf_model}.",
                installed_models=[self.hf_model],
            )

        has_hf_libs = self.check_transformers_installed()
        hf_note = (
            "PyTorch and Transformers are installed but no model is currently loaded in memory."
            if has_hf_libs
            else "PyTorch and Transformers are not installed in the active environment."
        )

        return LLMStatus(
            is_available=False,
            provider="offline_template_fallback",
            model_name="Template Fallback (Offline)",
            details=f"AI backend is currently unavailable (Groq key not configured/reached, and local Ollama at {self.ollama_url} unreachable). {hf_note}",
            installed_models=[],
            hardware_warning="For 24/7 cloud deployment, configure GROQ_API_KEY. For local use, run Ollama with qwen2.5-coder:1.5b.",
        )

    def generate_sql(
        self,
        question: str,
        schema_text: str,
        table_columns: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Generate candidate SQL from question and schema.

        When Groq or Ollama is online, ALWAYS executes real model inference.
        Never silently pretends that a fallback is an LLM.

        Returns:
            Dict containing:
                sql: Candidate SQL query string or None
                source: 'cloud_llm_groq' | 'local_llm_ollama' | 'local_llm_huggingface' | 'verified_demo_template' | 'unavailable'
                model: Identifier of the engine used
                explanation: Note regarding how query was produced
                raw_response: Raw output from model if available
                error: Error message if generation failed
        """
        clean_q = question.strip()
        if not clean_q:
            return {
                "sql": None,
                "source": "empty_input",
                "model": "None",
                "explanation": "No question provided.",
                "raw_response": None,
                "error": "Question is empty.",
            }

        status = self.get_status()

        # 1. Real Groq Cloud inference when connected
        if status.is_available and status.provider == "groq":
            try:
                payload = {
                    "model": status.model_name,
                    "messages": [
                        {"role": "system", "content": SQLGenerator.SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": f"{schema_text}\n\nUser Question: \"{clean_q}\"\n\nSQLite Query:",
                        },
                    ],
                    "temperature": SQL_TEMPERATURE,
                    "max_tokens": SQL_MAX_NEW_TOKENS,
                }
                resp = requests.post(
                    f"{self.groq_api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=20.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    candidate_sql = extract_sql_from_response(raw_text)
                    if candidate_sql:
                        return {
                            "sql": candidate_sql,
                            "source": "cloud_llm_groq",
                            "model": f"Groq Cloud ({status.model_name})",
                            "explanation": f"Generated by Groq Cloud model '{status.model_name}' (~0.5s inference).",
                            "raw_response": raw_text,
                            "error": None,
                        }
                    else:
                        return {
                            "sql": None,
                            "source": "groq_empty_sql",
                            "model": f"Groq Cloud ({status.model_name})",
                            "explanation": f"Groq model '{status.model_name}' did not return a valid SELECT query.",
                            "raw_response": raw_text,
                            "error": f"Groq Cloud model did not produce a valid SELECT query. Raw output:\n{raw_text}",
                        }
                else:
                    return {
                        "sql": None,
                        "source": "groq_http_error",
                        "model": f"Groq Cloud ({status.model_name})",
                        "explanation": f"Groq API returned HTTP {resp.status_code}.",
                        "raw_response": resp.text,
                        "error": f"Groq API request failed ({resp.status_code}): {resp.text}",
                    }
            except Exception as e:
                return {
                    "sql": None,
                    "source": "groq_error",
                    "model": f"Groq Cloud ({status.model_name})",
                    "explanation": "Connection to Groq Cloud API failed.",
                    "raw_response": None,
                    "error": f"Failed to communicate with Groq Cloud API: {str(e)}",
                }

        # 2. Real Ollama inference when connected
        if status.is_available and status.provider == "ollama":
            try:
                prompt = SQLGenerator.build_prompt(clean_q, schema_text)
                payload = {
                    "model": status.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": SQL_TEMPERATURE,
                        "num_predict": SQL_MAX_NEW_TOKENS,
                    },
                }
                resp = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30.0)
                if resp.status_code == 200:
                    raw_text = resp.json().get("response", "")
                    candidate_sql = extract_sql_from_response(raw_text)
                    if candidate_sql:
                        return {
                            "sql": candidate_sql,
                            "source": "local_llm_ollama",
                            "model": f"Ollama ({status.model_name})",
                            "explanation": f"Generated by real local LLM model '{status.model_name}' via Ollama.",
                            "raw_response": raw_text,
                            "error": None,
                        }
                    else:
                        return {
                            "sql": None,
                            "source": "ollama_empty_sql",
                            "model": f"Ollama ({status.model_name})",
                            "explanation": f"Ollama model '{status.model_name}' did not return a valid SELECT query.",
                            "raw_response": raw_text,
                            "error": f"The local model did not produce a valid SELECT query. Raw output:\n{raw_text}",
                        }
                else:
                    return {
                        "sql": None,
                        "source": "ollama_http_error",
                        "model": f"Ollama ({status.model_name})",
                        "explanation": f"Ollama returned HTTP {resp.status_code}.",
                        "raw_response": resp.text,
                        "error": f"Ollama API request failed with status code {resp.status_code}: {resp.text}",
                    }
            except Exception as e:
                return {
                    "sql": None,
                    "source": "ollama_error",
                    "model": f"Ollama ({status.model_name})",
                    "explanation": "Connection to Ollama failed.",
                    "raw_response": None,
                    "error": f"Failed to communicate with Ollama at {self.ollama_url}: {str(e)}",
                }

        # 2. Try Hugging Face pipeline if loaded
        if status.is_available and status.provider == "huggingface" and self._hf_pipeline is not None:
            try:
                prompt = SQLGenerator.build_prompt(clean_q, schema_text)
                out = self._hf_pipeline(prompt, max_new_tokens=SQL_MAX_NEW_TOKENS, temperature=0.01)
                raw_text = out[0]["generated_text"][len(prompt):]
                candidate_sql = extract_sql_from_response(raw_text)
                if candidate_sql:
                    return {
                        "sql": candidate_sql,
                        "source": "local_llm_huggingface",
                        "model": f"HuggingFace ({self.hf_model})",
                        "explanation": f"Generated by local in-memory Hugging Face model '{self.hf_model}'.",
                        "error": None,
                    }
            except Exception:
                pass

        # 3. Check for exact or normalized match against verified demo templates
        normalized_q = clean_q.lower().strip("?.! ")
        for demo_item in DEMO_QUESTIONS:
            demo_q = demo_item["question"].lower().strip("?.! ")
            if normalized_q == demo_q:
                return {
                    "sql": demo_item["sql"],
                    "source": "verified_demo_template",
                    "model": "Verified Question Template",
                    "explanation": f"Matched verified demo template query: '{demo_item['description']}' (Local LLM is offline).",
                    "error": None,
                }

        # 4. If table has uploaded single table, handle common simple intents deterministically
        if table_columns and len(table_columns) == 1:
            tbl_name = list(table_columns.keys())[0]
            cols = table_columns[tbl_name]
            # Match "how many rows", "count", "show all"
            if any(k in normalized_q for k in ["how many rows", "total rows", "count rows", "how many records"]):
                return {
                    "sql": f'SELECT COUNT(*) AS total_rows FROM "{tbl_name}";',
                    "source": "verified_pattern_template",
                    "model": "Pattern Matcher (Deterministic)",
                    "explanation": f"Matched counting query for table '{tbl_name}' (Local LLM is offline).",
                    "error": None,
                }
            if normalized_q in ["show all", "show data", "preview data", "display data", "view all"]:
                return {
                    "sql": f'SELECT * FROM "{tbl_name}" LIMIT 50;',
                    "source": "verified_pattern_template",
                    "model": "Pattern Matcher (Deterministic)",
                    "explanation": f"Matched preview query for table '{tbl_name}' (Local LLM is offline).",
                    "error": None,
                }

        # 5. Local LLM is unavailable and question is unmapped
        return {
            "sql": None,
            "source": "unavailable",
            "model": "None (Offline)",
            "explanation": "No AI model is currently active to translate arbitrary questions.",
            "error": (
                "AI backend is currently offline.\n\n"
                "To enable arbitrary AI question generation:\n"
                "1. Groq Cloud (Recommended for 24/7 web access): Configure GROQ_API_KEY in .env or Settings.\n"
                "2. Local Ollama: Start Ollama on your PC and run: `ollama run qwen2.5-coder:1.5b`.\n\n"
                "In the meantime, you can select any of the clickable Demo Questions above or test custom queries."
            ),
        }


# Type alias helper
Tuple_Check = tuple[bool, List[str]]
