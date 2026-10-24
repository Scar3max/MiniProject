
from groq import Groq
import sys
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except Exception:
    Llama = None
    LLAMA_AVAILABLE = False
from dotenv import load_dotenv
import re
import random
from typing import List, Optional, Dict, Any

from momentum_signal import compute_momentum
from syllabus_service import SyllabusService
import database

# --- 1. Configuration ---
load_dotenv()

# --- ⚠️ IMPORTANT: USER MUST CONFIGURE THESE ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SLM_MODEL_PATH = "qwen_interview_q4_k_m.gguf"
GROQ_MODEL_NAME = "qwen/qwen3.8-27b"

# Quality thresholds and tuning knobs
QUALITY_THRESHOLD = 7         # used to mark strong overall performance (logging)
DEEP_ESCALATION_THRESHOLD = 8.0  # >= this (and answer_type NORMAL) -> ask deeper/expert question
AVERAGE_LOWER = 6.5          # 6.5-7.9 considered average
WEAK_THRESHOLD = 6.5         # < this considered weak

# Momentum defaults (used when calling compute_momentum)
DEFAULT_MOMENTUM_NORM_DIV = 5.0
DEFAULT_MOMENTUM_WEIGHT = 1.25

# Forbidden robotic phrases (used by multiple prompts)
FORBIDDEN_TRANSITIONS = [
    "let's switch gears",
    "pivoting to a new topic",
    "understood, let's move on",
    "let's shift gears",
    "let's move on",
    "let's continue to",
    "let's change topic",
    "switching gears",
    "pivoting"
]

# --- 2. Prompts (The "Brains" of the Operation) ---
GLOBAL_INTERVIEWER_PROMPT = """
You are a calm, professional, and natural-sounding technical interviewer.
- Your tone is curious and encouraging, not robotic or like a textbook.
- You ask one short, focused question at a time (transition sentence optionally allowed).
- You do not use overly formal phrases like "Therefore" or "Moreover".
- You seamlessly adapt the conversation based on the candidate's performance.
- NEVER evaluate or judge the candidate's answers. Ban praise and achievement verdicts ("You nailed that", "Well explained", "Spot on", "Good detail", "Solid grasp"). Move straight to digging deeper.

**CRITICAL TONE RULE:**
Your transitions must be natural and conversational. Do NOT use robotic phrases like any of: {forbidden}
Do NOT use semicolons in your outputs. Short transition sentence (3-10 words) may be followed by a single question sentence.
"""

PROMPT_SYLLABUS_GENERATOR = """
You are an expert technical recruiter. Generate a JSON list of 5-7 *distinct, non-overlapping* key sub-topics for a 15-minute interview on the domain of '{domain}'.
Focus on *factual* areas. For example, for 'ML', topics should be like 'Supervised vs. Unsupervised', 'Regression Algorithms', 'Classification Metrics', 'Overfitting', 'Neural Networks'.
Avoid abstract topics like 'Problem Framing'.
Output *only* the JSON list.
"""

# [Call Type 1: Groq L0 Generator]
PROMPT_L0_GENERATOR = """
You are an expert technical interviewer. You are about to begin an interview in the domain: {domain}.

Generate exactly ONE concise, domain-factual opening question that:

- feels like a natural, light opening (you MAY include a short greeting like "Alright, let's begin," or "Great, to start,"),
- is simple, factual, and introductory,
- stays strictly within the technical domain (NO motivation/interest/personal questions),
- asks about a fundamental concept, principle, component, or mechanism,
- avoids deep theoretical math or highly advanced subtopics,
- is within ~18–20 words,
- is a single question (no multi-part),
- has no extra commentary or explanation,
- outputs ONLY the question (with greeting if used).

**STRICT RULE:** The question MUST be factual and technical.
Do NOT use any of these robotic phrases: {forbidden}
Output: one concise, factual opening question only.
"""

# [Call Type 2: Groq Analyzer/Judge/Strategist]
# NOTE: This prompt now includes the last 1-2 assistant questions (recent_questions)
PROMPT_ANALYZER = """
You are an expert interview judge and strategist. Your job is to analyze the candidate's last answer and provide a JSON-ONLY response to guide the next step.

**Context**
Question: {question}
Answer: {answer}
Recent_Assistant_Questions: {recent_questions_json}

====================================================
STRICT ANSWER CLASSIFICATION RULES (MATCH SYSTEM LOGIC)
====================================================

Before choosing `answer_type`, apply these exact rules:

1. HESITATION_SIGNAL (Highest Priority – Overrides ALL others)
- If the answer contains hesitation tokens: "umm", "uh", "uhh", "hmm", "er", "ah", "...", "uhm"
- OR includes trailing-off / half-sentences like "it works when the signal..."
- OR contains fewer than 3 meaningful words (ignore common fillers like "like", "sure", "okay", "well").

→ answer_type = HESITATION_SIGNAL

2. KNOWLEDGE_GAP (Only if user explicitly expresses not knowing)
- If the user writes "idk", "I don't know", "not sure", "pata nhi", "no idea", "haven't read", etc.
→ answer_type = KNOWLEDGE_GAP

3. EVASIVE_NON_ANSWER
- If user avoids answering without admitting ignorance: e.g., "can you rephrase?", "sure", "okay", "yes", "hmm", "I'll answer", "trying to think"
→ answer_type = EVASIVE_NON_ANSWER

4. EVASIVE_CHALLENGE
- If user challenges the interviewer: e.g., "stupid question", "you tell", "this is pointless", "chup kar"
→ answer_type = EVASIVE_CHALLENGE

5. FACTUALLY_INCORRECT
- If the content is confidently stated but factually wrong for the topic.
→ answer_type = FACTUALLY_INCORRECT

6. VAGUE
- On-topic, >3 meaningful words, not factually wrong, but missing core details.
→ answer_type = VAGUE

7. NORMAL
- Reasonably correct, enough detail, not hesitant, vague, or wrong.
→ answer_type = NORMAL

NOTE: The analyzer should provide a textual advisory score for human inspection only, but this orchestrator will IGNORE any numeric value from the analyzer and rely on a dedicated numeric scorer for decisions.

FOLLOW-UP QUESTION GUIDELINES:
- Your `strategic_question` must follow from the candidate's level, be factual, never repeat the same question,
  and shift to a related sub-concept if the user struggles.
- **Important:** If the proposed `strategic_question` would repeat any of the items in Recent_Assistant_Questions, choose a different, non-repeating strategic_question.
- **NON-REVEAL MANDATE:** If answer_type is FACTUALLY_INCORRECT, your `strategic_question` must NEVER state or reveal the correct answer as an established fact. Instead, ask a question that lets the candidate reconsider on their own or presents an open inquiry.

OUTPUT STRICTLY THIS JSON:
{{
  "content_summary": "<one-line neutral summary of candidate's answer>",
  "answer_quality_score": <float 0.0-10.0 rounded to 1 decimal, advisory only>,
  "answer_type": "<One of: 'Normal','Vague','HESITATION_SIGNAL','Factually_Incorrect','KNOWLEDGE_GAP','EVASIVE_NON_ANSWER','EVASIVE_CHALLENGE'>",
  "analysis_notes": "<one sentence explaining the classification and score>",
  "strategic_question": "<ONE factual follow-up question ONLY, not repeating recent assistant questions>",
  "topic_is_complete": false,
  "safety_violation": false,
  "terminate_interview": false,
  "reason_for_termination": null
}}
"""

# ---------------- NEW SCORER PROMPT (separate call) ----------------
PROMPT_SCORER = """
You are a strict numeric scorer for a short technical interview answer.
Input:
- Question: {question}
- Answer: {answer}

Output (JSON ONLY):
{{
  "score": <float between 0.0 and 10.0 rounded to 1 decimal>,
  "score_reason": "<one-sentence justification for the score>"
}}

SCORING RULES:
- 8.0–10.0: Correct, clear, and mostly complete.
- 5.0–7.9: Partially correct, some important details missing.
- 3.0–4.9: On-topic but vague or incomplete.
- 1.1–2.9: Attempted but factually incorrect.
- 0.0–1.0: Knowledge gap, hesitation, nonsense, or <3 meaningful words.

Round to one decimal place. Output valid JSON and nothing else.
"""

# [Call Type 3: Groq Expert/Fallback]
PROMPT_GROQ_EXPERT = """
{global_prompt}

You are taking over the conversation.
Interview Domain: {domain}
Full Conversation History:
{history}

Answer Classification: {answer_type_meta}
Recent Openers Used (DO NOT reuse or rephrase these): {recent_openers}
Strategic Hint: {hint}

=== OPENER & QUESTION RULES (apply BEFORE writing your question) ===

The opener is the short phrase BEFORE the question. Choose based on Answer Classification:

- HESITATION_SIGNAL:
  • Opener: short reassurance only, 6 words or fewer (e.g. "Take your time," / "No rush at all.").
  • Question: one SIMPLIFIED clarifying question, 12 words or fewer. Make it easier than the last one.
  • Do NOT reveal the answer. Do NOT acknowledge the hesitation explicitly.

- KNOWLEDGE_GAP:
  • Branch A — First poor signal on this subtopic (SUBTOPIC_STREAK: 1):
    - STAY on the SAME subtopic. Do NOT change topics.
    - Opener: non-judgmental transition phrase (<=6 words). Never use words like "struggle", "failed", "wrong", or "missed". Phrases like "Fair enough —" or "No worries at all —" are correct.
    - Question: ask a SIMPLER, more foundational question on the SAME underlying concept (<=18 words). Add helpful context or framing to make it approachable.
  • Branch B — Second consecutive poor signal on this subtopic (SUBTOPIC_STREAK >= 2):
    - Opener: soft redirect referencing that this area isn't clicking right now (e.g. "Fair enough, let's step back —").
    - Question: pivot to an accessible, foundational angle.

- FACTUALLY_INCORRECT:
  • CRITICAL NON-REVEAL RULE: NEVER state, confirm, or imply the correct answer as an established fact. Do NOT say "Since X is Y...", "Actually, X is Y...", or similar. Even if the hint mentions the correct term, you MUST NOT state or assert it as fact.
  • FIRST, check the [MOMENTUM: ...] tag in Answer Classification:
    - CASE 1: MOMENTUM is STRONG_NEGATIVE, MILD_NEGATIVE, or NEUTRAL (candidate is struggling or in a poor streak):
      STRICTLY FORBIDDEN: Do NOT offer binary choices. Do NOT challenge them ("are you sure?"). Do NOT put a struggling candidate on the spot to self-correct.
      REQUIRED: Ask a gentle reconsideration question exploring the mechanism without revealing the right answer (e.g. "Fair enough — if that were the case, how would concurrent updates avoid interfering with each other?").
    - CASE 2: MOMENTUM is STRONG_POSITIVE or MILD_POSITIVE (candidate has been doing well overall, this is an isolated slip):
      Give the candidate a direct chance to self-correct. Pick naturally between two forms (vary wording naturally):
        (a) Direct challenge with NO answer embedded: e.g. "Are you sure about that?" / "Want to double-check that part?" / "Take another look at that — are you certain?"
        (b) Forced binary choice presenting their term alongside the alternative as an open question, NOT as a verdict: e.g. "Is it [their term] or [alternative]?"
        CRITICAL FOR FORM (b): Frame as a genuine question. NEVER state "the answer is X, but you said Y". NEVER assert which option is right. The candidate must confirm or correct.
  • Opener: style C (neutral transition like "Fair enough —", "Alright then —", or none). Never use affirmations or praise.

- EVASIVE_NON_ANSWER:
  • Opener: a soft but firm redirect. Do NOT open a new topic. Steer directly back to the original question.
  • Example opener style: "That said, my question was specifically about..."
  • Do NOT sound impatient or repeat the same words verbatim from before.

- EVASIVE_CHALLENGE:
  • Opener: calm neutral transition. Do NOT apologize, do NOT justify why the question exists, do NOT match confrontation energy.
  • Example: "Let's keep going —" followed by re-asking a concrete version of the question.

- NORMAL (strong answer, score >= 8 — expert escalation):
  • Move directly to the harder follow-up with minimal preamble.
  • CRITICAL BAN ON EVALUATIVE LANGUAGE: Specific references must be used strictly to CONNECT to the next question, NEVER to evaluate or judge the candidate's answer.
  • Absolutely NO praise, achievement verdicts, or performance commentary: ban "nailed", "crushed", "exactly right", "spot on", "well explained", "good detail", "solid start", "great", "excellent".
  • WRONG: "You nailed that shared memory detail. How does the OS handle communication between separate processes?"
  • RIGHT: "Since threads in the same process share memory, how does the OS handle communication between two completely separate processes?"
  • The reference functions as a technical transition, not a verdict. Escalate to trade-offs, edge cases, implementation specifics, or comparisons.

=== SPECIFICITY & NO-EVALUATION RULE ===
Specific references to the candidate's answer MUST be used to CONNECT to the next question, NEVER to EVALUATE the answer just given.
- Do NOT comment on performance (NO "You nailed X", "Well explained", "Spot on", "Good detail on X", "Solid grasp").
- The specific reference functions as a transition or premise, not a verdict. Move immediately into the next question with no evaluative clause.
- This applies to NORMAL/strong answers. (For HESITATION_SIGNAL or KNOWLEDGE_GAP on first attempt, a general reassuring/neutral opener is correct).

=== OUTPUT FORMAT ===
- Up to TWO short sentences: opener (optional) + question (required).
- Do NOT use semicolons.
- Do NOT use any of the forbidden robotic phrases: {forbidden}.
- Do NOT repeat the exact last 1–2 assistant questions.
- Do NOT reuse or closely paraphrase any opener in: {recent_openers}

Output: exactly the opener (optional) plus the question (required), separated by a single space.
"""

# [Call Type 4: SLM Triage Prompt] (The "Smart Triage" prompt)
PROMPT_SLM_TRIAGE = """You are a professional technical interviewer for a campus SDE hiring interview, focused on {topic}. Ask thoughtful, adaptive follow-up questions based on the candidate's responses. Do NOT use robotic transition phrases like: {forbidden}. If the candidate's answer is complete nonsense or a non-answer (like 'yes' or 'sure'), respond ONLY with the single token `[CONFIDENCE_LOW]`."""

# [Call Type 5: Groq Refiner]
PROMPT_REFINER = """
{global_prompt}

You are an Editor-in-Chief for an AI interviewer. Create the perfect, concise follow-up.
You are given: the candidate's verbatim last answer, the Judge's one-line analysis, and a Draft question from the SLM triage model.

Candidate's Last Answer (verbatim):
"{user_answer}"

Judge's Analysis:
"{analysis_notes}"

SLM Draft Question:
"{slm_output}"

Extra Meta: {extra_meta}
Recent Openers Used (DO NOT reuse or rephrase these): {recent_openers}

=== OPENER RULES — choose based on [ANSWER_TYPE] in Extra Meta ===

Style palette (always available, mapped below by type):
  A) Brief neutral acknowledgments: "Alright," / "Got it," / "Makes sense,"
  B) Soft redirects: "Okay, building on that —" / "That touches on it —"
  C) Neutral transitions: "Sure," / "Alright then," / "Fair enough —"

- NORMAL (adequate answer):
  • Use style A or B strictly as a connective bridge into the next question, NEVER to evaluate or judge the answer.
  • CRITICAL BAN ON EVALUATIVE LANGUAGE: Absolutely NO evaluative praise or achievement-framed commentary. Ban words/phrases like "nailed", "crushed", "exactly right", "spot on", "well explained", "good detail", "solid start", "great", "excellent", or any phrasing that comments on how well the candidate did.
  • WRONG: "You nailed that shared memory detail. How does the OS handle communication between separate processes?"
  • RIGHT: "Since threads in the same process share memory, how does the OS handle communication between two completely separate processes?"
  • The specific reference must function strictly as a transition or premise, not a verdict. Escalate difficulty immediately.

- VAGUE:
  • Use style B (soft redirect).
  • Acknowledge what was said, then name the SPECIFIC missing piece from "{user_answer}".
  • Do NOT say "can you elaborate" or "tell me more".
  • Example: "That touches on it — you mentioned [their term], but how does [specific missing mechanism] work?"

- FACTUALLY_INCORRECT:
  • CRITICAL NON-REVEAL RULE: NEVER state, confirm, or imply the correct answer as an established fact. Even if the SLM draft or hint reveals the answer, you MUST STRIP IT OUT.
  • FIRST, check the [MOMENTUM: ...] tag in Extra Meta:
    - CASE 1: MOMENTUM is STRONG_NEGATIVE, MILD_NEGATIVE, or NEUTRAL (candidate is struggling or in a poor streak):
      STRICTLY FORBIDDEN: Do NOT offer binary choices. Do NOT challenge them ("are you sure?"). Do NOT put a struggling candidate on the spot to self-correct.
      REQUIRED: Ask a gentle reconsideration question exploring the mechanism without revealing the right answer (e.g. "Fair enough — if that were the case, how would the database handle concurrent transactions?").
    - CASE 2: MOMENTUM is STRONG_POSITIVE or MILD_POSITIVE (candidate has been doing well overall, this is an isolated slip):
      Give the candidate a direct chance to self-correct. Pick naturally between two forms (vary wording naturally):
        (a) Direct challenge with NO answer embedded: e.g. "Are you sure about that?" / "Want to double-check that part?" / "Take another look at that — are you certain?"
        (b) Forced binary choice presenting their term alongside the alternative as an open question, NOT as a verdict: e.g. "Is it [their term] or [alternative]?"
        CRITICAL FOR FORM (b): Frame as a genuine question. NEVER state "the answer is X, but you said Y". NEVER assert which option is right. The candidate must confirm or correct.
  • Opener: style C (neutral transition only, e.g. "Fair enough —", "Alright then —", or none). Never use affirmations (no "Got it", "Right", "Makes sense") which falsely imply correctness.

- EVASIVE_NON_ANSWER:
  • Use style B (soft redirect).
  • Firm but polite, explicitly steer back to the original question rather than opening a new one.
  • Example: "That said, what I was specifically asking was [paraphrase of original question]."

- EVASIVE_CHALLENGE:
  • Use style C (neutral transition).
  • Calm and unbothered in tone — do not mirror confrontation, do not over-explain or justify why the question stands.
  • Re-ask the question in a slightly different concrete form.

=== SPECIFICITY & NO-EVALUATION RULE ===
Specific references to the candidate's answer MUST be used to CONNECT to the next question, NEVER to EVALUATE the answer just given.
- Do NOT comment on performance (NO "You nailed X", "Well explained", "Spot on", "Good detail on X", "Solid grasp").
- The specific reference functions as a transition or technical premise, not a verdict.
- Move immediately into the next question with no evaluative clause in between.

=== QUESTION QUALITY RULES ===
- Do NOT just pick words from the candidate's answer and ask "what does X do?" or "how does X work?"
- DO ask about: concrete examples, implementation specifics, trade-offs, edge cases, mechanism comparisons.
- Question must be <= 20 words.

=== FORMAT ===
- Up to TWO short sentences: opener (0–1 sentences) + question (1 sentence).
- Do NOT use semicolons.
- Do NOT use any forbidden robotic transitions: {forbidden}.
- Do NOT repeat any of the last 1–2 assistant questions.
- Do NOT reuse any opener in: {recent_openers}, and avoid close variants of them (same structure with synonyms swapped).
- Output EXACTLY the opener (optional) plus the question (required), separated by a single space.
"""

# [Call Type 6: Groq Pivot Generator]
PROMPT_TOPIC_PIVOT = """
{global_prompt}

You are generating the FIRST question for a NEW topic: {topic}.

Input summary:
- Candidate Answer: "{user_answer}"
- Score: {score}
- Answer Type: {answer_type}
- Judge Notes: {analysis_notes}
- Recent Assistant Questions: {recent_questions_json}
- Recent Openers Used (DO NOT reuse or rephrase these): {recent_openers}

Task:
1) Produce up to TWO short sentences:
   - Sentence 1 (required for knowledge gaps or poor answers, optional otherwise): a conversational transition phrase (3–10 words) that bridges to the new topic. If the candidate had a knowledge gap or repeated poor answers, use a soft redirect style referencing that the previous area isn't clicking right now (e.g., "Fair enough, let's look at another angle.", "No worries, let's try a different direction.") rather than an abrupt flat question.
   - Sentence 2 (required): one factual theoretical interview level question about the new topic (<=20 words).
2) Do NOT use semicolons.
3) Do NOT use any forbidden robotic phrases: {forbidden}.
4) Do NOT repeat any of the items listed in Recent_Assistant_Questions.
5) Difficulty should depend on recent performance: easier if confused, moderate if average, deeper if confident.
6) Use a wide range of synonyms for acknowledgements and transitions.
7) The transition should connect naturally to the user's last response while smoothly guiding the conversation toward the pivot question.
8) Do NOT use praise or positive adjectives (fascinating, great, good, interesting, nice, excellent, etc.) if answer type is NOT Normal.
9) Do NOT reuse any opener in: {recent_openers}, and avoid close variants of them (same structure with synonyms swapped).
10) Output EXACTLY the transition and question (required) as 1-2 sentences.

Examples of valid output:
"Fair enough, let's look at another angle. What is the main function of MAC protocols?"
or
"No worries, let's try a different direction. What is the role of antenna diversity in wireless systems?"

Output only the transition+question text.
"""

# -------------------------
# InterviewOrchestrator class
# -------------------------
class InterviewOrchestrator:
    """
    Manages the ADAPTIVE interview flow, switching between SLM and Groq.
    Patches applied per user spec: analyzer receives last 1-2 assistant questions,
    2 consecutive hesitations -> knowledge gap, momentum normalization configurable,
    refined prompts forbidding robotic phrases and semicolons, and normalized outputs.

    KEY CHANGE: Analyzer numeric/advisory score is IGNORED for orchestration decisions.
               Numeric decisions rely on the dedicated Scorer (Groq Scorer).
               Pivot logic requires 2 consecutive STRONG_NEGATIVE momentum detections
               (grace window), tracked by self.pivot_grace_counter.
    """
    def __init__(self, domain, candidate_id: Optional[int] = None, session_id: Optional[int] = None, db_path: Optional[str] = None):
        self.domain = domain
        self.candidate_id = candidate_id
        self.session_id = session_id
        self.db_path = db_path
        self.turn_count = 0
        self.hesitation_streak = 0
        self.vague_streak = 0  # Track consecutive poor answers
        self.conversation_history = []
        self.last_question = ""
        self.low_score_streak = 0
        self.recent_scores = []   # holds last user scores for momentum computation

        self.topic_syllabus = []
        self.current_topic = ""
        # Track how many questions have been asked in the current topic
        self.questions_in_current_topic = 0

        # Rate limit tracking (for Streamlit compatibility)
        self.rate_limit_hit = False

        # pivot grace counter: require N consecutive strong-negative momentum detections before forcing pivot
        self.pivot_grace_counter = 0
        self.PIVOT_GRACE_REQUIRED = 2  # require 2 consecutive weak turns to pivot

        # Session-level opener deduplication (Change 5)
        self.recent_openers: List[str] = []  # stores last 3 extracted opener phrases

        # 1. Configure Groq
        print(f"Configuring Groq with model: {GROQ_MODEL_NAME}")
        self.groq_client = Groq(api_key=GROQ_API_KEY)

        # Initialize Syllabus Service
        self.syllabus_service = SyllabusService(self.groq_client)

        # 2. Configure SLM
        self.slm_model = None
        if LLAMA_AVAILABLE:
            try:
                print(f"Loading SLM from: {SLM_MODEL_PATH}...")
                print("This will take a moment as it loads...")
                start_load = time.time()
                self.slm_model = Llama(
                    model_path=SLM_MODEL_PATH,
                    n_gpu_layers=-1,
                    n_ctx=2048,
                    chat_format="chatml",
                    verbose=False
                )
                load_time = time.time() - start_load
                print(f"✅ SLM (GGUF) model loaded in {load_time:.2f} seconds.")
            except Exception as e:
                print(f"❌ FAILED TO LOAD SLM MODEL from {SLM_MODEL_PATH}")
                print(f"   Make sure 'SLM_MODEL_PATH' is correct.")
                print(f"   Error: {e}")
                print("   Will continue in Groq-only fallback mode.")
        else:
            print("⚠️ 'llama_cpp' module not available. Continuing in Groq-only fallback mode.")

        # 3. Generate the Syllabus
        self._generate_syllabus()

    def _generate_syllabus(self):
        """[Call 0] Generates the interview topic plan at the start."""
        print(f"\n...Generating interview syllabus for: {self.domain}...")
        try:
            # Use the new SyllabusService which handles caching
            syllabus = self.syllabus_service.get_syllabus(self.domain, PROMPT_SYLLABUS_GENERATOR)

            if not syllabus:
                raise ValueError("Syllabus is empty")
                
            self.topic_syllabus = syllabus

            print("...Shuffling syllabus topics...")
            random.shuffle(self.topic_syllabus)

            # 1. Force the {domain} to be the very first item in the list
            self.topic_syllabus.insert(0, self.domain)
            # 2. Now pop it. current_topic becomes {domain}, and the rest wait in the queue.
            self.current_topic = self.topic_syllabus.pop(0)
            # Reset topic question counter
            self.questions_in_current_topic = 0


            print(f"✅ Syllabus created. First topic: {self.current_topic}")
            print(f"   Remaining topics: {self.topic_syllabus}")

        except Exception as e:
            print(f"❌ FAILED TO GENERATE SYLLABUS. Error: {e}")
            print("...Defaulting to a single-topic interview.")
            self.current_topic = self.domain  # Fallback

    def start_interview(self):
        """[Call Type 1] Generates the first L0 question using Groq."""
        print(f"\n...Calling Groq for L0 question (Topic: {self.current_topic})...")

        forbidden_str = ", ".join([f'"{p}"' for p in FORBIDDEN_TRANSITIONS])
        prompt = PROMPT_L0_GENERATOR.format(
            domain=self.domain,
            forbidden=forbidden_str
        )

        response = self.groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
        )

        l0_question = self._normalize_output(response.choices[0].message.content.strip())
        self.last_question = l0_question
        self.conversation_history.append({"role": "assistant", "content": l0_question})
        self._track_opener(l0_question)
        return l0_question

    def _persist_turn(
        self,
        question_text: str,
        candidate_answer: str,
        subtopic: Optional[str],
        answer_classification: str,
        score: float,
        momentum_signal: Optional[str] = None,
        score_reason: Optional[str] = None,
        analysis_notes: Optional[str] = None
    ) -> Optional[int]:
        """Persists turn data to SQLite immediately if session_id is active."""
        if self.session_id is not None:
            self.turn_count += 1
            justification = database.format_judge_justification(score_reason, analysis_notes)
            try:
                turn_id = database.record_turn(
                    session_id=self.session_id,
                    turn_number=self.turn_count,
                    subtopic=subtopic,
                    question_text=question_text,
                    candidate_answer=candidate_answer,
                    answer_classification=answer_classification,
                    score=float(score) if score is not None else 0.0,
                    momentum_signal=momentum_signal,
                    judge_justification=justification,
                    db_path=self.db_path
                )
                print(f"...💾 Persisted turn #{self.turn_count} (turn_id={turn_id}) to DB.")
                return turn_id
            except Exception as e:
                print(f"...⚠️ Database record_turn failed: {e}")
        return None

    def end_session(self, final_summary: Optional[str] = None, overall_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Closes the current session row and recomputes candidate aggregates."""
        if self.session_id is not None:
            try:
                res = database.finish_session(
                    session_id=self.session_id,
                    final_summary=final_summary,
                    overall_score=overall_score,
                    db_path=self.db_path
                )
                print(f"...🏁 Session #{self.session_id} finished in DB. Candidate aggregates updated.")
                return res
            except Exception as e:
                print(f"...⚠️ Database finish_session failed: {e}")
        return None

    def _normalize_output(self, text: str) -> str:
        """
        Cleans up the bot's response to ensure a consistent, human tone.
        Key fixes:
        - Remove semicolons.
        - Replace robotic glue phrases.
        - Ensure proper punctuation (one question mark if missing).
        - Prevent double spaces and trailing punctuation.
        - Keep up to 2 sentences (transition + question) if present.
        """
        if not text:
            return text

        # Strip surrounding whitespace and quotes
        text = text.strip().strip('"').strip("'")

        # Replace a few canned formal connectors with friendlier phrases
        text = text.replace("Therefore,", "So,")
        text = text.replace("Moreover,", "Also,")
        text = text.replace("In conclusion,", "Ultimately,")

        # Remove semicolons entirely
        text = text.replace(";", ",")

        # Remove forbidden robotic phrases (case-insensitive)
        for phrase in FORBIDDEN_TRANSITIONS:
            pattern = re.compile(re.escape(phrase), flags=re.IGNORECASE)
            text = pattern.sub("", text)

        # Collapse multiple punctuation/whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+([?.!,])', r'\1', text)
        text = re.sub(r'([?.!,]){2,}', r'\1', text)

        # Ensure the output ends with punctuation; if the last sentence seems to be a question, ensure '?'
        if not re.search(r'[.?!"\']$', text):
            # if likely a question (contains words like what, why, how, when, which, describe), add '?'
            if re.search(r'\b(what|why|how|when|which|describe|explain|tell)\b', text.lower()):
                text = text + "?"
            else:
                text = text + "."

        # Trim to at most two sentences.
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 2:
            sentences = sentences[-2:]  # keep last two sentences (transition+question preferred)
        # Reconstruct with single space
        final = " ".join(s.strip() for s in sentences).strip()

        # Final safety: remove leading/trailing punctuation anomalies
        final = final.strip()
        final = re.sub(r'^[\s\.,;:]+', '', final)
        final = re.sub(r'[\s\.,;:]+$', '', final)

        return final

    def _extract_opener(self, text: str) -> str:
        """
        Extract the opener clause (the leading transition phrase before the question).
        Heuristic: take the leading clause before the question up to the first comma, period,
        exclamation mark, or em-dash. If the message starts directly with the question, return "".
        """
        if not text:
            return ""
        qmark_idx = text.find('?')
        pre_q = text[:qmark_idx] if qmark_idx != -1 else text
        m = re.match(r'^([^?]{2,60}?[,.!—])\s+', pre_q)
        if m:
            candidate = m.group(1).strip()
            if len(candidate.split()) <= 12 and '?' not in candidate:
                return candidate
        return ""

    def _track_opener(self, final_text: str) -> None:
        """
        Extract the opener from the final output and store it in self.recent_openers.
        Keeps only the last 3 openers.
        """
        opener = self._extract_opener(final_text)
        if opener:
            self.recent_openers.append(opener)
            if len(self.recent_openers) > 3:
                self.recent_openers = self.recent_openers[-3:]

    def _get_recent_assistant_questions(self, n: int = 2) -> List[str]:
        """
        Return the last n assistant questions content (most recent first).
        """
        assistant_qs = [turn['content'] for turn in reversed(self.conversation_history) if turn['role'] == 'assistant']
        return assistant_qs[:n]

    def _get_groq_analysis(self, question: str, answer: str):
        """[Call Type 2] Calls Groq to analyze and classify the answer (Analyzer).
        NOTE: The numeric 'answer_quality_score' produced by analyzer is advisory only and
        intentionally IGNORED by the orchestrator. We still rely on analyzer for 'answer_type',
        'analysis_notes', and 'strategic_question' textual guidance.
        """
        print("\n...Calling Groq (Judge/Strategist) for analysis...")
        recent_qs = self._get_recent_assistant_questions(2)
        try:
            recent_json = json.dumps(recent_qs)
        except:
            recent_json = "[]"

        prompt = PROMPT_ANALYZER.format(
            question=question,
            answer=answer,
            recent_questions_json=recent_json
        )
        try:
            response = self.groq_client.chat.completions.create(
                model=GROQ_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            clean_response = response.choices[0].message.content.strip()
            analysis = json.loads(clean_response)

            def to_bool(val):
                if isinstance(val, bool):
                    return val
                return str(val).lower() == 'true'

            analysis['terminate_interview'] = to_bool(analysis.get('terminate_interview'))
            # Keep analyzer's topic_is_complete parsed but we will not rely on it for orchestrator decisions per user instruction
            analysis['topic_is_complete'] = to_bool(analysis.get('topic_is_complete'))

            return analysis

        except Exception as e:
            print(f"❌ Error parsing Groq analysis JSON: {e}")
            try:
                raw = response.choices[0].message.content
            except:
                raw = "<no raw response>"
            print(f"   Raw response: {raw}")
            return {
                "content_summary": "Analysis failed",
                "answer_quality_score": 0.0,
                "answer_type": "Normal",
                "analysis_notes": "JSON parsing error.",
                "strategic_question": "Ask a simple, re-phrased question.",
                "topic_is_complete": False,
                "terminate_interview": False,
                "reason_for_termination": "Analysis Error"
            }

    def _get_groq_score(self, question: str, answer: str):
        """NEW: [Call SCORER] Calls Groq with the separate scoring prompt and returns a float score and reason."""
        print("\n...Calling Groq (Scorer) for numeric score...")
        prompt = PROMPT_SCORER.format(question=question, answer=answer)
        try:
            response = self.groq_client.chat.completions.create(
                model=GROQ_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            clean_response = response.choices[0].message.content.strip()
            score_json = json.loads(clean_response)
            # Ensure rounding to 1 decimal
            score_val = float(score_json.get("score", 0.0))
            # Clamp between 0 and 10
            if score_val < 0.0:
                score_val = 0.0
            if score_val > 10.0:
                score_val = 10.0
            # Round to 1 decimal
            score_val = round(score_val, 1)
            score_reason = str(score_json.get("score_reason", "")).strip()
            print(f"...Scorer returned: {score_val} — {score_reason}")
            return {"score": score_val, "score_reason": score_reason}
        except Exception as e:
            print(f"❌ Scorer call or JSON parse failed: {e}")
            try:
                raw = response.choices[0].message.content
            except:
                raw = "<no raw response>"
            print(f"   Raw scorer response: {raw}")
            # Important: DO NOT fallback to analyzer numeric score; instead return failure indicator
            return {"score": None, "score_reason": "Scorer failed"}

    def _get_slm_triage_question(self):
        """[Call Type 4] Calls the local SLM to *think*."""
        if self.slm_model is None:
            print("...SLM not loaded. Skipping...")
            return None

        print("...Calling local SLM (Triage) to *think*...")

        forbidden_str = ", ".join([f'"{p}"' for p in FORBIDDEN_TRANSITIONS])
        system_content = PROMPT_SLM_TRIAGE.format(
            topic=self.current_topic,
            forbidden=forbidden_str
        )

        messages = []
        messages.append({"role": "system", "content": system_content})
        messages.extend(self.conversation_history)

        try:
            # Conservative SLM call: short, low temperature for concise drafts
            output = self.slm_model.create_chat_completion(
                messages=messages,
                max_tokens=80,   # shorter drafts
                stop=["<|end|>", "<|user|>", "You:", "Candidate:", "Interviewer:"],
                temperature=0.25  # conservative, less creative
            )
            next_question = output['choices'][0]['message']['content'].strip()

            if not next_question:
                print("...SLM FAILED (empty response).")
                return None

            # If SLM itself returned the bailout token, accept it.
            if "[CONFIDENCE_LOW]" in next_question:
                print("...SLM successfully triggered [CONFIDENCE_LOW].")
                return "[CONFIDENCE_LOW]"

            # Post-validate the SLM question: require at least 3 meaningful words,
            # and reject if it contains hesitation tokens or ellipses.
            def meaningful_word_count(s):
                # remove common filler tokens and punctuation, then count words of length>1
                fillers = {"umm", "ummm", "uh", "uhh", "hmm", "er", "ah", "like", "...", "uhm"}
                tokens = re.findall(r"[A-Za-z']+", s.lower())
                meaningful = [t for t in tokens if t not in fillers and len(t) > 1]
                return len(meaningful)

            hesitation_tokens = ["umm", "ummm", "uh", "uhh", "hmm", "er", "ah", "...", "uhm"]

            if any(tok in next_question.lower() for tok in hesitation_tokens):
                print("...SLM output contains hesitation tokens; treating as [CONFIDENCE_LOW].")
                return "[CONFIDENCE_LOW]"

            if meaningful_word_count(next_question) < 3:
                print("...SLM output too short (fewer than 3 meaningful words); treating as [CONFIDENCE_LOW].")
                return "[CONFIDENCE_LOW]"

            # All checks passed — accept SLM draft.
            print(f"...SLM (Triage) generated draft: \"{next_question}\"")
            return next_question

        except Exception as e:
            print(f"...SLM FAILED (Exception): {e}")
            return None

    def _get_groq_expert_question(self, hint: str, answer_type: str = "NORMAL", poor_streak: int = 1, momentum: str = "NEUTRAL"):
        """[Call Type 3] Calls Groq for an "Expert" or "Fallback" question."""
        print(f"...Calling Groq (Expert/Fallback). hint={hint!r}, answer_type={answer_type!r}, poor_streak={poor_streak}, momentum={momentum!r}")

        history_str = ""
        for turn in self.conversation_history:
            role = "Interviewer" if turn['role'] == 'assistant' else "Candidate"
            history_str += f"{role}: {turn['content']}\n"

        answer_type_meta = f"[ANSWER_TYPE: {answer_type}] [SUBTOPIC_STREAK: {poor_streak}] [MOMENTUM: {momentum}]"
        recent_openers_str = json.dumps(self.recent_openers) if self.recent_openers else "[]"

        prompt = PROMPT_GROQ_EXPERT.format(
            global_prompt=GLOBAL_INTERVIEWER_PROMPT.format(
                forbidden=", ".join([f'"{p}"' for p in FORBIDDEN_TRANSITIONS])
            ),
            domain=self.domain,
            history=history_str,
            answer_type_meta=answer_type_meta,
            recent_openers=recent_openers_str,
            hint=hint,
            forbidden=", ".join([f'"{p}"' for p in FORBIDDEN_TRANSITIONS])
        )

        response = self.groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def _get_groq_refinement(self, user_answer: str, analysis_notes: str, slm_output: str, hint: str, answer_type: str = None, momentum: str = "NEUTRAL"):
        """[Call Type 5] Calls Groq "Editor" to create the final, concise response. momentum={momentum!r}..."""

        # Compose extra_meta from explicit answer_type (if provided).
        if answer_type:
            extra_meta = f"[ANSWER_TYPE: {answer_type}] [MOMENTUM: {momentum}]"
        else:
            extra_meta = f"[ANSWER_TYPE: NORMAL] [MOMENTUM: {momentum}]"

        # Provide recent assistant questions to the refiner so it doesn't repeat.
        recent_qs = self._get_recent_assistant_questions(2)
        extra_meta = extra_meta + f" [RECENT_ASSISTANT_QS: {json.dumps(recent_qs)}]"

        recent_openers_str = json.dumps(self.recent_openers) if self.recent_openers else "[]"

        prompt = PROMPT_REFINER.format(
            global_prompt=GLOBAL_INTERVIEWER_PROMPT.format(
                forbidden=", ".join([f'"{p}"' for p in FORBIDDEN_TRANSITIONS])
            ),
            user_answer=user_answer,
            analysis_notes=analysis_notes,
            slm_output=slm_output,
            extra_meta=extra_meta,
            recent_openers=recent_openers_str,
            forbidden=", ".join([f'"{p}"' for p in FORBIDDEN_TRANSITIONS])
        )

        response = self.groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def _get_groq_pivot_question(self, new_topic: str, user_answer: str, score, answer_type: str, analysis_notes: str):
        """[Call Type 6] Calls Groq to get a new L0 question for a topic pivot."""
        print(f"...Calling Groq (Pivot) for new L0 question on: {new_topic}...")

        recent_qs = self._get_recent_assistant_questions(2)
        recent_json = json.dumps(recent_qs)
        recent_openers_str = json.dumps(self.recent_openers) if self.recent_openers else "[]"

        prompt = PROMPT_TOPIC_PIVOT.format(
            global_prompt=GLOBAL_INTERVIEWER_PROMPT.format(
                forbidden=", ".join([f'"{p}"' for p in FORBIDDEN_TRANSITIONS])
            ),
            topic=new_topic,
            user_answer=user_answer,
            score=score,
            answer_type=answer_type,
            analysis_notes=analysis_notes,
            recent_questions_json=recent_json,
            recent_openers=recent_openers_str,
            forbidden=", ".join([f'"{p}"' for p in FORBIDDEN_TRANSITIONS])
        )

        response = self.groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def _evaluate_answer_parallel(self, question: str, answer: str):
        """[Call Parallel Evaluation] Evaluates classification and scoring concurrently."""
        print("\n...Parallel evaluation started...")
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            analysis_future = executor.submit(self._get_groq_analysis, question, answer)
            score_future = executor.submit(self._get_groq_score, question, answer)
            
            analysis = analysis_future.result()
            score_result = score_future.result()
            
        elapsed = time.perf_counter() - start_time
        print(f"...Parallel evaluation completed in {elapsed:.2f}s")
        return analysis, score_result

    def process_user_answer(self, user_answer: str):
        
        self.conversation_history.append({"role": "user", "content": user_answer})
        
        # Capture question and subtopic being answered this turn before state updates
        turn_question_text = self.last_question
        turn_subtopic = self.current_topic

        # Concurrent evaluation
        analysis, score_result = self._evaluate_answer_parallel(turn_question_text, user_answer)

        # Extract classification and notes from analyzer
        answer_type = analysis.get("answer_type", "Normal")
        
        # REPETITION DETECTION: Check if user is repeating the same vague answer
        def _detect_repetitive_answer_inline(current_answer):
            # Get recent user answers
            user_answers = [turn['content'] for turn in reversed(self.conversation_history) if turn['role'] == 'user']
            recent_answers = user_answers[:3]
            if len(recent_answers) < 2:
                return False
            # Extract key words
            common_words = {'the', 'a', 'an', 'is', 'are', 'it', 'that', 'this', 'through', 'by', 'with', 'as', 'i', 'said', 'yeah', 'bro'}
            current_words = set(current_answer.lower().split()) - common_words
            # Check similarity
            similar_count = 0
            for prev_answer in recent_answers[1:]:
                prev_words = set(prev_answer.lower().split()) - common_words
                if len(current_words) > 0 and len(prev_words) > 0:
                    intersection = current_words & prev_words
                    union = current_words | prev_words
                    similarity = len(intersection) / len(union) if len(union) > 0 else 0
                    if similarity > 0.6:
                        similar_count += 1
            return similar_count >= 2
        
        if _detect_repetitive_answer_inline(user_answer):
            print(f"...🔁 REPETITION DETECTED: User is repeating similar vague answers.")
            if answer_type not in ("KNOWLEDGE_GAP", "EVASIVE_CHALLENGE", "EVASIVE_NON_ANSWER"):
                answer_type = "VAGUE"
                analysis["answer_type"] = "VAGUE"
                analysis["analysis_notes"] = "Repetitive answer without adding new information."


        # Track consecutive hesitations
        if answer_type == "HESITATION_SIGNAL":
            self.hesitation_streak += 1
        else:
            self.hesitation_streak = 0

        # Track consecutive poor signals: VAGUE, FACTUALLY_INCORRECT, EVASIVE_NON_ANSWER, EVASIVE_CHALLENGE, HESITATION_SIGNAL, KNOWLEDGE_GAP
        if answer_type in ("VAGUE", "FACTUALLY_INCORRECT", "EVASIVE_NON_ANSWER", "EVASIVE_CHALLENGE", "HESITATION_SIGNAL", "KNOWLEDGE_GAP"):
            self.vague_streak += 1
            print(f"...Poor answer streak: {self.vague_streak} (type: {answer_type})")
        else:
            self.vague_streak = 0

        mercy_pivot_triggered = False

        # AUTO-CONVERT 2 consecutive poor answers into Mercy Pivot
        if self.vague_streak >= 2:
            mercy_pivot_triggered = True
            topic_complete_flag = True
            print(f"...🚨 MERCY PIVOT: {self.vague_streak} consecutive poor answers on '{self.current_topic}' → pivoting to next topic.")
            hint = f"Candidate is struggling with '{self.current_topic}' ({self.vague_streak} consecutive poor/gap answers). Pivot smoothly to the next topic: '{self.topic_syllabus[0] if self.topic_syllabus else 'a new area'}'."
            score = 0.0
            momentum_causes_forced_pivot = False
            self.vague_streak = 0  # Reset
            self.hesitation_streak = 0  # Also reset hesitation

        # AUTO-CONVERT 2 consecutive hesitations into Mercy Pivot
        elif self.hesitation_streak >= 2:
            mercy_pivot_triggered = True
            topic_complete_flag = True
            print(f"...🚨 MERCY PIVOT: Multiple consecutive hesitations → pivoting to next topic.")
            hint = f"Candidate hesitating repeatedly on '{self.current_topic}'. Pivot smoothly to the next topic: '{self.topic_syllabus[0] if self.topic_syllabus else 'a new area'}'."
            score = 0.0
            momentum_causes_forced_pivot = False
            self.vague_streak = 0
            self.hesitation_streak = 0

        analysis_notes = analysis.get("analysis_notes", "") if isinstance(analysis, dict) else ""
        score_reason = score_result.get("score_reason", "") if isinstance(score_result, dict) else ""
        hint = analysis.get("strategic_question", "Ask a logical follow-up.")
        topic_complete_flag = mercy_pivot_triggered

        # ------------- Priority 1: Safety / Immediate Termination -------------
        if analysis.get("terminate_interview", False):
            reason = analysis.get("reason_for_termination", "Safety violation or candidate refusal.")
            print(f"\nTERMINATING INTERVIEW. Reason: {reason}")
            self._persist_turn(
                question_text=turn_question_text,
                candidate_answer=user_answer,
                subtopic=turn_subtopic,
                answer_classification=analysis.get("answer_type", "Violation"),
                score=0.0,
                momentum_signal=None,
                score_reason=score_reason,
                analysis_notes=analysis_notes or reason
            )
            return {"status": "TERMINATED", "analysis": analysis}

        # ------------- Priority 2: Knowledge Gap handling -------------
        # On FIRST Knowledge Gap (streak=1), do NOT pivot! Simplify on the same subtopic.
        if answer_type == "KNOWLEDGE_GAP" and not mercy_pivot_triggered:
            print(f"...First KNOWLEDGE_GAP on '{self.current_topic}' (streak=1). Simplifying on SAME subtopic (no pivot yet).")
            topic_complete_flag = False
            hint = (f"Candidate indicated a knowledge gap on the current question in '{self.current_topic}'. "
                    f"Do NOT change topic. Ask a SIMPLER, more foundational question on the SAME subtopic '{self.current_topic}' "
                    f"with approachable context and framing.")
            score = 0.0
            momentum_causes_forced_pivot = False
        elif not mercy_pivot_triggered:
            # ------------- Extract the separate parallel score -------------
            score = score_result.get("score", None) if isinstance(score_result, dict) else None

            # If scorer failed, do NOT fallback to analyzer numeric score.
            if score is None:
                # fallback: last known valid score or 0.0
                last_valid = None
                for s in reversed(self.recent_scores):
                    try:
                        if s is not None:
                            last_valid = float(s)
                            break
                    except:
                        continue
                if last_valid is not None:
                    score = round(last_valid, 1)
                    print(f"...Scorer failed. Falling back to last known score: {score}")
                else:
                    score = 0.0
                    print("...Scorer failed. No previous score found. Using conservative score: 0.0")
            else:
                # we have a valid scorer value
                pass

        # Trajectory entering this turn (candidate's baseline momentum before current answer)
        prior_momentum_info = compute_momentum(self.recent_scores,
                                               normalization_divisor=DEFAULT_MOMENTUM_NORM_DIV,
                                               weight=DEFAULT_MOMENTUM_WEIGHT)
        prior_momentum_signal = prior_momentum_info['signal']

        # Maintain recent scores for momentum and density (oldest...newest)
        try:
            self.recent_scores.append(float(score))
        except:
            self.recent_scores.append(0.0)

        if len(self.recent_scores) > 10:
            self.recent_scores = self.recent_scores[-10:]

        # Compute sliding-window momentum signal (uses normalization_divisor and weight)
        momentum_info = compute_momentum(self.recent_scores,
                                        normalization_divisor=DEFAULT_MOMENTUM_NORM_DIV,
                                        weight=DEFAULT_MOMENTUM_WEIGHT)
        momentum_signal = momentum_info['signal']
        momentum_norm = momentum_info['norm']
        momentum_weighted = momentum_info['weighted']

        # For FACTUALLY_INCORRECT: if candidate was trending positive entering this question,
        # it is an isolated slip (STRONG_POSITIVE / MILD_POSITIVE).
        if prior_momentum_signal in ("STRONG_POSITIVE", "MILD_POSITIVE"):
            effective_momentum = prior_momentum_signal
        elif prior_momentum_signal in ("STRONG_NEGATIVE", "MILD_NEGATIVE") or momentum_signal in ("STRONG_NEGATIVE", "MILD_NEGATIVE"):
            effective_momentum = "STRONG_NEGATIVE" if "STRONG" in (prior_momentum_signal, momentum_signal) else "MILD_NEGATIVE"
        else:
            effective_momentum = momentum_signal

        # Debug output for momentum
        print(f"...[MOMENTUM DEBUG] raw={momentum_info['raw']:.3f}, norm={momentum_norm:.3f}, "
              f"weighted={momentum_weighted:.3f}, signal={momentum_signal}, effective_momentum={effective_momentum}")

        # Update low_score_streak for logging/observability (use scorer-derived score)
        if float(score) <= 1.5:
            self.low_score_streak += 1
            print(f"...Low score streak is now: {self.low_score_streak}")
        else:
            self.low_score_streak = 0

        # Grade letter (for logs)
        grade_letter = "A"
        if score <= 1.5:
            grade_letter = "L"
        elif score >= QUALITY_THRESHOLD:
            grade_letter = "H"

        print(f"...Score ({score}) [{grade_letter}] Analysis...")

        # ------- Minimal density-based fallback (replaces hard strike-limit) -------
        density_window = 2  # Reduced for faster pivot
        density_thresh = 0.75  # e.g., 75% of window being L triggers pivot
        recent_for_density = self.recent_scores[-density_window:]
        low_count = sum(1 for s in recent_for_density if s <= 1.5)
        low_density_trigger = (len(recent_for_density) == density_window and (low_count / density_window) >= density_thresh)

        # ------- Momentum-influenced policy adjustments (soft MP3) -------
        momentum_causes_forced_pivot = (momentum_signal == "STRONG_NEGATIVE")
        # Prevent momentum-caused pivot if knowledge gap was detected earlier
        if answer_type == "KNOWLEDGE_GAP":
            momentum_causes_forced_pivot = False

        next_question = None

        # ---------------- ROUTING LOGIC (preserve original priorities) ----------------
        # 3. Judge's (Groq) pivot — NOT used for topic_is_complete orchestration, but keep compatibility:
        # We will ignore analysis['topic_is_complete'] for automatic pivoting to avoid false positives.

        # 4. Behavioral interceptors (EVASIVE / CHALLENGE)
        if answer_type == "EVASIVE_NON_ANSWER":
            print(f"...User is stalling. Calling Groq (Expert) to be firm.")
            hint = f"The candidate is stalling ('{user_answer}'). Politely but firmly, re-ask the last question: '{self.last_question}'"
            next_question = self._get_groq_expert_question(hint=hint, answer_type=answer_type, poor_streak=self.vague_streak, momentum=effective_momentum)

        elif answer_type == "EVASIVE_CHALLENGE":
            print(f"...User is challenging. Calling Groq (Expert) to restate role.")
            hint = f"The candidate is challenging ('{user_answer}'). Politely restate your role as the interviewer and then re-ask the last question: '{self.last_question}'"
            next_question = self._get_groq_expert_question(hint=hint, answer_type=answer_type, poor_streak=self.vague_streak, momentum=effective_momentum)

        # ---------- BEGIN: PRIORITIZED HESITATION / KNOWLEDGE / PIVOT GUARDS ----------
        # Optional: Hesitation shortcut — prefer a short clarifying question and skip pivots
        if answer_type == "HESITATION_SIGNAL" and next_question is None and not topic_complete_flag:
            print("...Answer marked HESITATION_SIGNAL. Using Groq Expert to produce a short clarifying question.")
            hint = f"Candidate hesitated on '{self.current_topic}'. Ask a short, simple clarifying question (<=12 words)."
            next_question = self._get_groq_expert_question(hint=hint, answer_type=answer_type, poor_streak=self.hesitation_streak, momentum=effective_momentum)

        # First Knowledge Gap on subtopic: simplify on SAME subtopic, DO NOT pivot
        if answer_type == "KNOWLEDGE_GAP" and next_question is None and not topic_complete_flag:
            print(f"...Answer marked KNOWLEDGE_GAP (first attempt on '{self.current_topic}'). Calling Groq Expert to simplify on the same subtopic.")
            hint = (f"Candidate has a knowledge gap on the current question in '{self.current_topic}'. "
                    f"Do NOT change topic. Ask a SIMPLER, more foundational question on the SAME subtopic '{self.current_topic}' "
                    f"with approachable framing and context.")
            next_question = self._get_groq_expert_question(hint=hint, answer_type=answer_type, poor_streak=1, momentum=effective_momentum)

        # If Groq Expert already produced a next_question (e.g., from EVASIVE_* or HESITATION),
        # we prefer that expert-crafted question and skip pivoting logic this turn.
        expert_escalation_present = (next_question is not None)

        # ------- Natural "topic complete" detection (soft, human-like) -------
        # This orchestration respects your instruction: do not depend on analyzer.topic_is_complete
        natural_topic_complete = False
        try:
            if (not expert_escalation_present) and answer_type not in ("HESITATION_SIGNAL", "KNOWLEDGE_GAP"):
                if len(self.recent_scores) >= 3 and all(s >= 7.0 for s in self.recent_scores[-3:]) and momentum_weighted >= 0.0:
                    natural_topic_complete = True
                elif len(self.recent_scores) >= 4 and (sum(self.recent_scores[-4:]) / 4.0) >= 6.0 and momentum_weighted >= 0.0:
                    natural_topic_complete = True
                else:
                    natural_topic_complete = False
        except Exception:
            natural_topic_complete = False

        if natural_topic_complete:
            # Block natural topic completion if fewer than 2 questions asked
            if self.questions_in_current_topic < 2:
                print("...Natural topic completion triggered early but BLOCKED (min 2 questions rule).")
                natural_topic_complete = False
            else:
                print("...Natural topic completion detected by recent scorer pattern. Preparing to pivot.")
                topic_complete_flag = True
                hint = f"Candidate has demonstrated stable competence on '{self.current_topic}'. Pivot to next topic: '{self.topic_syllabus[0] if self.topic_syllabus else 'a new area'}'."

        # ------- Momentum & Density pivots (run ONLY if no higher-priority expert actions) -------
        allow_pivot_checks = (not topic_complete_flag) and (not expert_escalation_present) and (answer_type not in ("HESITATION_SIGNAL", "KNOWLEDGE_GAP"))

        if allow_pivot_checks:
            # 5. Momentum forced pivot (soft) with grace window requiring consecutive detections
            if momentum_causes_forced_pivot:
                # If momentum negative, increment grace counter. Only pivot after PIVOT_GRACE_REQUIRED consecutive detections.
                if self.pivot_grace_counter < (self.PIVOT_GRACE_REQUIRED - 1):
                    self.pivot_grace_counter += 1
                    print(f"...Momentum negative detected (grace {self.pivot_grace_counter}/{self.PIVOT_GRACE_REQUIRED}). Not pivoting yet.")
                    # Do not pivot this turn; treat as not forcing pivot
                    momentum_causes_forced_pivot = False
                else:
                    # this is the Nth consecutive negative detection -> pivot now
                    print(f"...Momentum signal STRONG_NEGATIVE after grace window → pivot.")
                    topic_complete_flag = True
                    hint = f"Candidate shows a clear declining trend on '{self.current_topic}'. Pivot to next topic: '{self.topic_syllabus[0] if self.topic_syllabus else 'a new area'}'."
                    # reset low score streak only for safety
                    self.low_score_streak = 0
                    # reset pivot grace counter after pivot
                    self.pivot_grace_counter = 0
            else:
                # momentum not negative -> reset grace counter (break consecutive streak)
                if self.pivot_grace_counter != 0:
                    print("...Momentum recovered or not negative — resetting pivot grace counter.")
                self.pivot_grace_counter = 0

            # 6. Low-score density fallback (conservative)
            if low_density_trigger and answer_type != "EVASIVE_NON_ANSWER":
                print(f"...Low-score density detected ({low_count}/{density_window}). Forcing a pivot.")
                topic_complete_flag = True
                hint = f"Multiple weak answers on '{self.current_topic}'. Pivoting to next topic: '{self.topic_syllabus[0] if self.topic_syllabus else 'a new area'}'."
                self.low_score_streak = 0
                # reset pivot grace counter since we pivot due to density
                self.pivot_grace_counter = 0
        # ---------- END: PRIORITIZED HESITATION / KNOWLEDGE / PIVOT GUARDS ----------

        # 7. Topic Pivot handling
        if topic_complete_flag:
            # If pivot was caused by mercy pivot (2 consecutive poor answers/gaps), bypass min-2 check
            if not mercy_pivot_triggered:
                if self.questions_in_current_topic < 2:
                    print("...Pivot blocked: fewer than 2 questions asked in this topic. Continuing within the same topic.")
                    topic_complete_flag = False
                    self._persist_turn(
                        question_text=turn_question_text,
                        candidate_answer=user_answer,
                        subtopic=turn_subtopic,
                        answer_classification=answer_type,
                        score=float(score) if score is not None else 0.0,
                        momentum_signal=momentum_signal,
                        score_reason=score_reason,
                        analysis_notes=analysis_notes
                    )
                    return {
                        "status": "CONTINUE",
                        "next_question": self.last_question,
                        "analysis": analysis
                    }

            # ---- Continue with normal pivot ----
            print(f"...Topic '{self.current_topic}' is complete. Pivoting...")
            self.low_score_streak = 0


            if not self.topic_syllabus:
                print("...Syllabus complete. Ending interview.")
                self._persist_turn(
                    question_text=turn_question_text,
                    candidate_answer=user_answer,
                    subtopic=turn_subtopic,
                    answer_classification=answer_type,
                    score=float(score) if score is not None else 0.0,
                    momentum_signal=momentum_signal,
                    score_reason=score_reason,
                    analysis_notes=analysis_notes
                )
                return {"status": "TERMINATED", "analysis": analysis, "reason": "SyllabusFinished"}

            self.current_topic = self.topic_syllabus.pop(0)
            print(f"...Pivoting to new topic: {self.current_topic}")
            self.questions_in_current_topic = 0

            next_question = self._get_groq_pivot_question(
                new_topic=self.current_topic,
                user_answer=user_answer,
                score=score,
                answer_type=answer_type,
                analysis_notes=analysis_notes
            )

        # 8. Default 'Fusion Pass' (SLM triage + Groq refinement)
        elif next_question is None:
            # NEW: Expert escalation for truly strong NORMAL answers (skip SLM triage, ask deeper expert Q)
            if answer_type == "NORMAL" and float(score) >= DEEP_ESCALATION_THRESHOLD:
                print(f"...Strong NORMAL answer detected (score={score}). Escalating to expert-level follow-up.")
                expert_hint = ("Candidate appears well-read. Ask a deeper, expert-level technical follow-up. "
                               "You may include a short formula, a comparison, or ask for trade-offs. "
                               "Do NOT use praise words.")
                next_question = self._get_groq_expert_question(hint=expert_hint, answer_type="NORMAL", poor_streak=0, momentum=effective_momentum)

            else:
                print(f"...Score ({score}) routed to Fusion Pass (SLM -> Groq Editor).")
                slm_draft_question = self._get_slm_triage_question()

                if slm_draft_question is None or slm_draft_question == "[CONFIDENCE_LOW]":
                    print("...SLM failed or escalated. Calling Groq (Fallback).")
                    fallback_hint = f"Candidate's score was {score} and the SLM (TFailure) failed. Use this hint: {hint}"
                    next_question = self._get_groq_expert_question(hint=fallback_hint, answer_type=answer_type, poor_streak=self.vague_streak, momentum=effective_momentum)
                else:
                    # pass answer_type to refiner via extra_meta so it can adapt wording
                    next_question = self._get_groq_refinement(
                        user_answer=user_answer,
                        analysis_notes=analysis_notes,
                        slm_output=slm_draft_question,
                        hint=hint,
                        answer_type=answer_type,
                        momentum=effective_momentum
                    )

        normalized_question = self._normalize_output(next_question)
        self.last_question = normalized_question
        self.conversation_history.append({"role": "assistant", "content": normalized_question})
        # Count this question toward topic depth
        self.questions_in_current_topic += 1
        # Session-level opener deduplication: track the opener phrase
        self._track_opener(normalized_question)


        # Attach the latest score into the analysis return for user debugging
        analysis_return = analysis.copy()
        analysis_return['score_used'] = round(float(score), 1) if isinstance(score, (int, float)) else score

        self._persist_turn(
            question_text=turn_question_text,
            candidate_answer=user_answer,
            subtopic=turn_subtopic,
            answer_classification=answer_type,
            score=float(score) if score is not None else 0.0,
            momentum_signal=momentum_signal,
            score_reason=score_reason,
            analysis_notes=analysis_notes
        )

        return {"status": "CONTINUE", "next_question": normalized_question, "analysis": analysis_return}

