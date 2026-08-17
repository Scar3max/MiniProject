import time
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from interview import InterviewOrchestrator

def sequential_evaluation(orchestrator, question, answer):
    start = time.perf_counter()
    analysis = orchestrator._get_gemini_analysis(question, answer)
    score_result = orchestrator._get_gemini_score(question, answer)
    elapsed = time.perf_counter() - start
    return elapsed, analysis, score_result

def parallel_evaluation(orchestrator, question, answer):
    start = time.perf_counter()
    analysis, score_result = orchestrator._evaluate_answer_parallel(question, answer)
    elapsed = time.perf_counter() - start
    return elapsed, analysis, score_result

def main():
    print("--- Evaluation Benchmarking ---")
    
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Warning: GOOGLE_API_KEY missing. Network latency won't be accurately measured without actual API calls.")
        
    orchestrator = InterviewOrchestrator("Python")
    
    question = "Can you explain what a decorator is in Python?"
    answer = "A decorator is a design pattern in Python that allows a user to add new functionality to an existing object without modifying its structure. They are usually called before the definition of a function you want to decorate."
    
    print("\nStarting benchmark (3 runs each)...")
    
    # Warmup
    print("Warming up Gemini API...")
    try:
        orchestrator._get_gemini_score("Hi", "Hello")
    except:
        pass
        
    seq_times = []
    print("\n--- Sequential Runs ---")
    for i in range(3):
        t, _, _ = sequential_evaluation(orchestrator, question, answer)
        seq_times.append(t)
        print(f"Run {i+1}: {t:.2f}s")
        
    par_times = []
    print("\n--- Parallel Runs ---")
    for i in range(3):
        t, _, _ = parallel_evaluation(orchestrator, question, answer)
        par_times.append(t)
        print(f"Run {i+1}: {t:.2f}s")
        
    print("\n--- Results ---")
    print(f"Sequential Avg: {sum(seq_times)/len(seq_times):.2f}s")
    print(f"Parallel Avg:   {sum(par_times)/len(par_times):.2f}s")

if __name__ == "__main__":
    main()
