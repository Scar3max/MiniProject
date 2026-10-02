import sqlite3
import json
import time
import os
import logging
import contextlib
from groq import Groq

SYLLABUS_VERSION = "v1"

# Configure lightweight logging
logger = logging.getLogger("syllabus_cache")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class SyllabusService:
    def __init__(self, groq_client, db_path="interview_cache.db"):
        self.db_path = db_path
        self.groq_client = groq_client
        self.hits = 0
        self.misses = 0
        self._init_db()

    def _init_db(self):
        # NOTE: If we scaled to multiple instances, we would need distributed locking or Redis.
        # SQLite is sufficient for the current architecture.
        try:
            with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS syllabus_cache (
                            domain TEXT NOT NULL,
                            version TEXT NOT NULL,
                            syllabus TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (domain, version)
                        )
                    """)
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def get_syllabus(self, domain, prompt_template):
        """
        Retrieves syllabus for the domain.
        First checks the cache, on miss generates via Groq and stores it.
        """
        start_time = time.time()
        
        # 1. Cache lookup
        cached_syllabus = self._read_from_cache(domain)
        if cached_syllabus:
            self.hits += 1
            latency = time.time() - start_time
            print(f"[CACHE HIT] syllabus domain={domain} version={SYLLABUS_VERSION}")
            logger.info(f"[Syllabus] domain={domain} cache=HIT latency={latency:.3f}s")
            self._print_stats()
            return cached_syllabus

        # 2. Cache miss -> Groq generation
        self.misses += 1
        print(f"[CACHE MISS] syllabus domain={domain} version={SYLLABUS_VERSION}")
        print(f"[GROQ] generating syllabus domain={domain} version={SYLLABUS_VERSION}")
        
        syllabus = self._generate_syllabus_with_groq(domain, prompt_template)
        
        # 3. Save to cache
        if syllabus:
            self._save_to_cache(domain, syllabus)
            latency = time.time() - start_time
            logger.info(f"[Syllabus] domain={domain} cache=MISS latency={latency:.3f}s")
            self._print_stats()
            return syllabus
            
        return None

    def _read_from_cache(self, domain):
        try:
            with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT syllabus FROM syllabus_cache WHERE domain = ? AND version = ?",
                    (domain, SYLLABUS_VERSION)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"Cache read failure: {e}")
        return None

    def _save_to_cache(self, domain, syllabus):
        try:
            with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
                with conn:
                    # INSERT OR REPLACE handles duplicates safely (thread-safe for simple cases)
                    conn.execute(
                        "INSERT OR REPLACE INTO syllabus_cache (domain, version, syllabus) VALUES (?, ?, ?)",
                        (domain, SYLLABUS_VERSION, json.dumps(syllabus))
                    )
            print(f"[CACHE STORE] syllabus domain={domain} version={SYLLABUS_VERSION}")
        except Exception as e:
            logger.error(f"Cache write failure: {e}")

    def _generate_syllabus_with_groq(self, domain, prompt_template):
        try:
            prompt = prompt_template.format(domain=domain)
            response = self.groq_client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            clean_response = response.choices[0].message.content.strip()
            syllabus = json.loads(clean_response)
            return syllabus
        except Exception as e:
            logger.error(f"Groq syllabus generation failed: {e}")
            return None

    def clear_cache(self, domain=None, version=None):
        """
        Cache management method.
        Can clear entirely, by domain, or by domain+version.
        """
        try:
            with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
                with conn:
                    if domain and version:
                        conn.execute("DELETE FROM syllabus_cache WHERE domain = ? AND version = ?", (domain, version))
                        print(f"Cleared cache for {domain}:{version}")
                    elif domain:
                        conn.execute("DELETE FROM syllabus_cache WHERE domain = ?", (domain,))
                        print(f"Cleared cache for {domain}")
                    else:
                        conn.execute("DELETE FROM syllabus_cache")
                        print("Cleared entire syllabus cache")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    def _print_stats(self):
        total = self.hits + self.misses
        if total > 0:
            rate = self.hits / total
            print(f"[CACHE STATS] Hits: {self.hits}, Misses: {self.misses}, Hit Rate: {rate:.2%}")

# Expose a global method for easy cache clearing from outside (e.g., admin console)
def clear_syllabus_cache(domain=None, version=None, db_path="interview_cache.db"):
    service = SyllabusService(groq_client=None, db_path=db_path)
    service.clear_cache(domain, version)
