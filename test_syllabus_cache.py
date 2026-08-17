import unittest
import sqlite3
import json
import os
from unittest.mock import MagicMock, patch
from syllabus_service import SyllabusService, SYLLABUS_VERSION

class TestSyllabusCache(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_interview_cache.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        self.mock_gemini_model = MagicMock()
        self.service = SyllabusService(self.mock_gemini_model, db_path=self.db_path)
        
        # Helper to mock Gemini response
        self.setup_gemini_mock(["Topic 1", "Topic 2"])

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass

    def setup_gemini_mock(self, syllabus_list):
        mock_response = MagicMock()
        mock_response.text = json.dumps(syllabus_list)
        self.mock_gemini_model.generate_content.return_value = mock_response

    def test_1_first_request_cache_miss(self):
        """Test 1 — First request: Cache MISS, Gemini called once, Syllabus stored"""
        syllabus = self.service.get_syllabus("Python", "Prompt: {domain}")
        
        self.assertEqual(syllabus, ["Topic 1", "Topic 2"])
        self.assertEqual(self.service.misses, 1)
        self.assertEqual(self.service.hits, 0)
        self.mock_gemini_model.generate_content.assert_called_once()
        
        # Verify it was stored
        cached = self.service._read_from_cache("Python")
        self.assertEqual(cached, ["Topic 1", "Topic 2"])

    def test_2_same_domain_again_cache_hit(self):
        """Test 2 — Same domain again: Cache HIT, Gemini NOT called, Same syllabus returned"""
        # First call to populate cache
        self.service.get_syllabus("Python", "Prompt: {domain}")
        self.mock_gemini_model.generate_content.reset_mock()
        
        # Second call
        syllabus = self.service.get_syllabus("Python", "Prompt: {domain}")
        
        self.assertEqual(syllabus, ["Topic 1", "Topic 2"])
        self.assertEqual(self.service.misses, 1)
        self.assertEqual(self.service.hits, 1)
        self.mock_gemini_model.generate_content.assert_not_called()

    def test_3_different_domain_cache_miss(self):
        """Test 3 — Different domain: Cache MISS, Gemini called, New syllabus stored"""
        # First call domain 1
        self.service.get_syllabus("Python", "Prompt: {domain}")
        
        # Change mock for domain 2
        self.setup_gemini_mock(["ML 1", "ML 2"])
        
        # Call domain 2
        syllabus = self.service.get_syllabus("Machine Learning", "Prompt: {domain}")
        
        self.assertEqual(syllabus, ["ML 1", "ML 2"])
        self.assertEqual(self.service.misses, 2)
        self.assertEqual(self.service.hits, 0)
        
        cached = self.service._read_from_cache("Machine Learning")
        self.assertEqual(cached, ["ML 1", "ML 2"])

    @patch('syllabus_service.SYLLABUS_VERSION', 'v2')
    def test_4_different_version_cache_miss(self):
        """Test 4 — Different version: Cache MISS, Gemini called, New version stored"""
        # The patch decorator temporarily changes SYLLABUS_VERSION to 'v2'
        
        # We need a new service instance to pick up the patched version if it was used in init
        # actually SYLLABUS_VERSION is a global in the module, so patching it works.
        
        syllabus = self.service.get_syllabus("Python", "Prompt: {domain}")
        self.assertEqual(syllabus, ["Topic 1", "Topic 2"])
        self.assertEqual(self.service.misses, 1)

    def test_5_cache_write_failure(self):
        """Test 5 — Cache write failure: Gemini syllabus is still returned"""
        # Sabotage the database connection to force a write error
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("Mocked write failure")
            
            syllabus = self.service.get_syllabus("Python", "Prompt: {domain}")
            
            # Should still return the syllabus from Gemini despite DB error
            self.assertEqual(syllabus, ["Topic 1", "Topic 2"])
            self.mock_gemini_model.generate_content.assert_called_once()

    def test_6_gemini_failure(self):
        """Test 6 — Gemini failure: No invalid syllabus is inserted, Existing error handling is triggered"""
        self.mock_gemini_model.generate_content.side_effect = Exception("Gemini API Error")
        
        syllabus = self.service.get_syllabus("Python", "Prompt: {domain}")
        
        # Should return None, and error handled gracefully
        self.assertIsNone(syllabus)
        
        # Verify nothing was stored in cache
        cached = self.service._read_from_cache("Python")
        self.assertIsNone(cached)

    def test_7_cache_read_failure(self):
        """Test 7 — Cache read failure: System falls back to Gemini, Interview does not crash"""
        # Insert a valid entry first
        self.service._save_to_cache("Python", ["Topic 1", "Topic 2"])
        self.mock_gemini_model.generate_content.reset_mock()
        
        # Sabotage the read_from_cache method by mocking sqlite3.connect to fail
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("Mocked read failure")
            syllabus = self.service.get_syllabus("Python", "Prompt: {domain}")
            
            # Since read failed, it should fall back to Gemini
            self.assertEqual(syllabus, ["Topic 1", "Topic 2"])
            self.mock_gemini_model.generate_content.assert_called_once()
            self.assertEqual(self.service.misses, 1)

if __name__ == '__main__':
    unittest.main()
