import os
from dotenv import load_dotenv
import google.generativeai as genai
from syllabus_service import SyllabusService, clear_syllabus_cache

def main():
    print("--- Developer Cache Verification ---\n")
    
    # 1. Clear the cache first to ensure a clean state
    clear_syllabus_cache()
    print()
    
    # 2. Setup Gemini (Requires GOOGLE_API_KEY)
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] GOOGLE_API_KEY not found in environment. Mocking Gemini call for verification.")
        
        class MockGemini:
            def generate_content(self, prompt, generation_config=None):
                import json
                class MockResponse:
                    @property
                    def text(self):
                        if "Python" in prompt:
                            return json.dumps(["Python Basics", "OOP", "Decorators"])
                        elif "Machine Learning" in prompt:
                            return json.dumps(["Supervised", "Unsupervised", "Neural Nets"])
                        return json.dumps(["Topic 1", "Topic 2"])
                return MockResponse()
                
        gemini_model = MockGemini()
    else:
        print("[OK] Using real Gemini model.")
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel("gemini-2.5-flash")

    # 3. Create service
    service = SyllabusService(gemini_model=gemini_model)
    prompt_template = "Generate syllabus for {domain}. Return ONLY a JSON list of 3 topics."

    print("\n--- Request 1: Python ---")
    syllabus = service.get_syllabus("Python", prompt_template)
    print(f"Result: {syllabus}")

    print("\n--- Request 2: Python (Should hit cache) ---")
    syllabus2 = service.get_syllabus("Python", prompt_template)
    print(f"Result: {syllabus2}")

    print("\n--- Request 3: Machine Learning ---")
    syllabus3 = service.get_syllabus("Machine Learning", prompt_template)
    print(f"Result: {syllabus3}")

    print("\n--- Request 4: Machine Learning (Should hit cache) ---")
    syllabus4 = service.get_syllabus("Machine Learning", prompt_template)
    print(f"Result: {syllabus4}")
    
    print("\n[OK] Verification complete.")

if __name__ == "__main__":
    main()
