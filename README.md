# 🎯 Adaptive Performance-Based Interview Bot

An AI-powered technical interview companion that dynamically adjusts its questions, difficulty, and topics in real-time based on the candidate's answers. Built with a hybrid Edge-Cloud LLM architecture utilizing a local Small Language Model (SLM) for drafting and the Groq API for strategic evaluation.

---

## ✨ Features

- **Hybrid Edge-Cloud Architecture**: Combines local Qwen2.5-7B-Instruct SLM (via Llama.cpp) and cloud-based Groq API.
- **Dynamic Difficulty & Pivoting**: Automatically detects knowledge gaps, hesitation patterns, and performance trend signals to adjust difficulty or pivot sub-topics.
- **Real-Time Badges**: Displays immediate feedback (e.g., *Good Answer*, *Vague*, *Incorrect*, *Hesitation*) as the candidate responds.
- **Rich Analytics Dashboard**: Renders interactive Plotly charts showing score trends, answer quality distribution, and personalized qualitative AI feedback.
- **Natural Tone Enforcement**: Automatically monitors and filters robotic transitions to keep the dialogue conversational and human-like.

---

## 🛠️ Tech Stack

- **Frontend**: Streamlit (Glassmorphism dark theme)
- **Backend Orchestrator**: Python (`groq`, `llama-cpp-python`)
- **Performance Analysis**: Plotly
- **Models**:
  - Cloud: Qwen 3.8 27B (via Groq — `qwen/qwen3.8-27b`)
  - Edge: Qwen2.5-7B-Instruct (fine-tuned, GGUF Q4_K_M format)

---

## 🚀 Setup & Installation

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd interview-framework
```

### 2. Install Dependencies
Make sure you have Python 3.8+ installed. Install the required libraries:
```bash
pip install -r requirements.txt
```
*(Note: To run the local SLM, ensure you have `llama-cpp-python` installed. You may need build tools like CMake for your specific OS/GPU setup).*

### 3. Configure Environment Variables
Create a `.env` file in the root directory and add your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Download the GGUF Model
Because the 7.6GB Small Language Model file (`*.gguf`) is too large for GitHub, it is excluded via `.gitignore`. 
- Download your fine-tuned Qwen2.5-7B-Instruct model file (`qwen_interview_q4_k_m.gguf` or similar).
- Place the `.gguf` file in the **root** of the project directory.
- Update the filename path in `interview.py` (around line 19) if needed:
  ```python
  SLM_MODEL_PATH = "qwen_interview_q4_k_m.gguf"
  ```

---

## 🏃 Running the Application

Start the Streamlit server:
```bash
streamlit run streamlit_app.py
```
Open the local URL displayed in your terminal (usually `http://localhost:8501`) to start your practice interview.

---

## 👨‍💻 Contributors

- **Created by**: Aayush Tripathi (ECE Department, LNMIIT)
- **Supervised by**: Dr. Nishant Gupta (Assistant Professor, LNMIIT)
