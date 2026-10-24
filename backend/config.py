"""
backend/config.py - Environment and application configuration for FastAPI backend.
"""

import os
from typing import List

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_NAME: str = os.getenv("GROQ_MODEL_NAME", "qwen/qwen3.8-27b")
SLM_MODEL_PATH: str = os.getenv("SLM_MODEL_PATH", "qwen_interview_q4_k_m.gguf")

JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-super-secure-secret-key-interview-framework-2026")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))  # 7 days

COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "true" if os.getenv("ENV") == "production" else "false").lower() in ("true", "1", "yes")
COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")

MIN_COHORT_CANDIDATES: int = int(os.getenv("MIN_COHORT_CANDIDATES", "5"))
SESSION_IDLE_TIMEOUT_HOURS: int = int(os.getenv("SESSION_IDLE_TIMEOUT_HOURS", "2"))

DATABASE_PATH: str = os.getenv("DATABASE_PATH", os.getenv("INTERVIEW_DB_PATH", "interview_history.db"))

CORS_ORIGINS: List[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
