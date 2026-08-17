import unittest
import time
import threading
from unittest.mock import MagicMock, patch
from interview import InterviewOrchestrator

class TestParallelEvaluation(unittest.TestCase):
    def setUp(self):
        # We patch LLAMA available so it doesn't try to load the heavy model
        patcher = patch('interview.LLAMA_AVAILABLE', False)
        self.addCleanup(patcher.stop)
        patcher.start()
        
        # Patch init syllabus generation so it doesn't hit Gemini
        with patch.object(InterviewOrchestrator, '_generate_syllabus', return_value=None):
            self.orchestrator = InterviewOrchestrator("Test Domain")

        self.question = "What is a test?"
        self.answer = "A test is a test."

    @patch.object(InterviewOrchestrator, '_get_gemini_analysis')
    @patch.object(InterviewOrchestrator, '_get_gemini_score')
    def test_1_both_evaluators_execute(self, mock_score, mock_analysis):
        """Test 1 — Both evaluators execute once"""
        mock_analysis.return_value = {"answer_type": "Normal"}
        mock_score.return_value = {"score": 8.5, "score_reason": "Good"}

        self.orchestrator._evaluate_answer_parallel(self.question, self.answer)

        mock_analysis.assert_called_once()
        mock_score.assert_called_once()

    @patch.object(InterviewOrchestrator, '_get_gemini_analysis')
    @patch.object(InterviewOrchestrator, '_get_gemini_score')
    def test_2_correct_arguments(self, mock_score, mock_analysis):
        """Test 2 — Both evaluators receive the correct arguments"""
        mock_analysis.return_value = {"answer_type": "Normal"}
        mock_score.return_value = {"score": 8.5, "score_reason": "Good"}

        self.orchestrator._evaluate_answer_parallel(self.question, self.answer)

        mock_analysis.assert_called_with(self.question, self.answer)
        mock_score.assert_called_with(self.question, self.answer)

    @patch.object(InterviewOrchestrator, '_get_gemini_analysis')
    @patch.object(InterviewOrchestrator, '_get_gemini_score')
    def test_3_results_are_preserved(self, mock_score, mock_analysis):
        """Test 3 — Results are exactly preserved"""
        expected_analysis = {"answer_type": "Normal", "notes": "Test notes"}
        expected_score = {"score": 8.0, "score_reason": "Clear explanation"}

        mock_analysis.return_value = expected_analysis
        mock_score.return_value = expected_score

        analysis, score_result = self.orchestrator._evaluate_answer_parallel(self.question, self.answer)

        self.assertEqual(analysis, expected_analysis)
        self.assertEqual(score_result, expected_score)

    @patch.object(InterviewOrchestrator, '_get_gemini_analysis')
    @patch.object(InterviewOrchestrator, '_get_gemini_score')
    def test_4_classification_failure(self, mock_score, mock_analysis):
        """Test 4 — Classification failure propagates/preserves original behavior"""
        # The project originally allowed exception to bubble up if we didn't catch it
        # Actually `_get_gemini_analysis` has its own try/except returning a fallback dict.
        # But if the orchestrator's concurrency layer swallowed exceptions, it would be bad.
        # Let's force an exception directly to ensure the ThreadPoolExecutor propagates it.
        mock_analysis.side_effect = Exception("Classification failed")
        mock_score.return_value = {"score": 8.0, "score_reason": "Good"}

        with self.assertRaisesRegex(Exception, "Classification failed"):
            self.orchestrator._evaluate_answer_parallel(self.question, self.answer)

    @patch.object(InterviewOrchestrator, '_get_gemini_analysis')
    @patch.object(InterviewOrchestrator, '_get_gemini_score')
    def test_5_scoring_failure(self, mock_score, mock_analysis):
        """Test 5 — Scoring failure propagates"""
        mock_analysis.return_value = {"answer_type": "Normal"}
        mock_score.side_effect = Exception("Scoring failed")

        with self.assertRaisesRegex(Exception, "Scoring failed"):
            self.orchestrator._evaluate_answer_parallel(self.question, self.answer)

    @patch.object(InterviewOrchestrator, '_get_gemini_analysis')
    @patch.object(InterviewOrchestrator, '_get_gemini_score')
    def test_6_concurrency(self, mock_score, mock_analysis):
        """Test 6 — Concurrency proven using threading Events"""
        # We will use two events to ensure that one thread doesn't finish until the other has started,
        # proving they overlap in time.
        
        analysis_started = threading.Event()
        score_started = threading.Event()

        def mock_analysis_side_effect(q, a):
            analysis_started.set()
            # Wait for score to start before finishing
            score_started.wait(timeout=2)
            return {"answer_type": "Normal"}

        def mock_score_side_effect(q, a):
            score_started.set()
            # Wait for analysis to start before finishing
            analysis_started.wait(timeout=2)
            return {"score": 8.0, "score_reason": "Good"}

        mock_analysis.side_effect = mock_analysis_side_effect
        mock_score.side_effect = mock_score_side_effect

        start_time = time.time()
        self.orchestrator._evaluate_answer_parallel(self.question, self.answer)
        elapsed = time.time() - start_time
        
        # If they were sequential, one would deadlock and timeout (taking ~2 seconds)
        # If concurrent, they finish almost immediately.
        self.assertTrue(analysis_started.is_set())
        self.assertTrue(score_started.is_set())
        self.assertLess(elapsed, 1.0, "Functions did not execute concurrently (timed out waiting for overlap)")

if __name__ == '__main__':
    unittest.main()
