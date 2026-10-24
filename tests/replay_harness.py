"""
tests/replay_harness.py - Deterministic Replay Harness for Interview Transcripts
Replays golden fixtures deterministically across interview services without live LLM network calls.
"""

import json
import os
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

import database
import interview_service
import analytics_service
from interview import InterviewOrchestrator


class MockChatCompletionChoice:
    def __init__(self, content: str):
        self.message = MagicMock()
        self.message.content = content


class MockChatCompletionResponse:
    def __init__(self, content: str):
        self.choices = [MockChatCompletionChoice(content)]


class DeterministicReplayHarness:
    """
    Simulates Groq API responses based on pre-recorded golden fixture data.
    """

    def __init__(self, fixture_path: str):
        with open(fixture_path, "r", encoding="utf-8") as f:
            self.fixture = json.load(f)

        self.domain = self.fixture["domain"]
        self.candidate_identifier = self.fixture.get("candidate_identifier", "test-replay-user")
        self.syllabus = self.fixture["syllabus"]
        self.opening_question = self.fixture["opening_question"]
        self.turns = self.fixture["turns"]

    def run_replay(self, db_path: str) -> Dict[str, Any]:
        """
        Runs the full interview session through interview_service using mocked LLM responses.
        """
        mock_syllabus_service = MagicMock()
        mock_syllabus_service.get_syllabus.return_value = list(self.syllabus)
        mock_syllabus_service.get_opening_question.return_value = self.opening_question

        turn_idx = [0]

        def mock_create(*args, **kwargs):
            messages = kwargs.get("messages", [])
            prompt_content = messages[-1].get("content", "") if messages else ""

            # 1. Opening L0 question
            if "begin an interview in the domain" in prompt_content or "Generate exactly ONE concise" in prompt_content:
                return MockChatCompletionResponse(self.opening_question)

            # 2. Strict Numeric Scorer
            if "strict numeric scorer" in prompt_content or "Output (JSON ONLY):" in prompt_content:
                current_turn = self.turns[turn_idx[0]]
                analysis_data = current_turn.get("analysis") or {}
                score_val = analysis_data.get("score_used") or analysis_data.get("answer_quality_score") or 8.0
                reason_val = analysis_data.get("justification") or "Accurate answer."
                return MockChatCompletionResponse(json.dumps({
                    "score": float(score_val),
                    "score_reason": reason_val
                }))

            # 3. Judge / Strategist Analysis
            if "expert interview judge and strategist" in prompt_content or "Analyze this technical interview response" in prompt_content:
                current_turn = self.turns[turn_idx[0]]
                analysis_data = current_turn.get("analysis") or {
                    "answer_quality_score": 5.0,
                    "answer_type": "NORMAL",
                    "justification": "Mocked",
                    "technical_depth": "Intermediate",
                    "subtopic": self.domain
                }
                return MockChatCompletionResponse(json.dumps(analysis_data))

            # 4. Next Question Generation (Refiner, Groq Expert, Pivot)
            current_turn = self.turns[turn_idx[0]]
            next_q = current_turn.get("next_question") or "Mocked follow up question?"
            return MockChatCompletionResponse(next_q)

        mock_groq = MagicMock()
        mock_groq.chat.completions.create.side_effect = mock_create

        with patch("interview.Groq", return_value=mock_groq), \
             patch("interview.SyllabusService", return_value=mock_syllabus_service), \
             patch("interview.LLAMA_AVAILABLE", False):

            # 1. Start interview
            start_result = interview_service.start_interview_session(
                selected_domain=self.domain,
                candidate_identifier=self.candidate_identifier,
                db_path=db_path
            )

            assert start_result["status"] == "STARTED", f"Failed start: {start_result}"
            assert start_result["question"] == self.opening_question
            session_id = start_result["session_id"]
            chatbot = start_result["chatbot"]

            recorded_outcomes = []

            # 2. Replay each turn
            for i, turn_data in enumerate(self.turns):
                turn_idx[0] = i
                candidate_answer = turn_data["candidate_answer"]

                outcome = interview_service.process_candidate_answer(
                    chatbot=chatbot,
                    user_answer=candidate_answer
                )
                recorded_outcomes.append(outcome)

                expected_status = turn_data["expected_status"]
                assert outcome["status"] == expected_status, f"Turn {i+1}: expected status {expected_status}, got {outcome['status']}"

                if expected_status == "TERMINATED":
                    if "expected_reason" in turn_data:
                        assert outcome.get("reason") == turn_data["expected_reason"], f"Turn {i+1}: expected reason {turn_data['expected_reason']}, got {outcome.get('reason')}"
                    break
                else:
                    if turn_data.get("next_question"):
                        assert outcome["next_question"] == turn_data["next_question"]

            # 3. Finalize interview session
            final_res = interview_service.finalize_interview_session(
                session_id=session_id,
                chatbot=chatbot,
                candidate_id=start_result["candidate_id"],
                db_path=db_path
            )

            db_turns = database.get_session_turns(session_id, db_path=db_path)
            stats = final_res["stats"]

            return {
                "session_id": session_id,
                "start_result": start_result,
                "outcomes": recorded_outcomes,
                "final_res": final_res,
                "db_turns": db_turns,
                "stats": stats
            }
