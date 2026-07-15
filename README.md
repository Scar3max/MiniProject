# 🎯 Adaptive Performance-Based Interview Bot

An AI-powered technical interview companion that dynamically adjusts its questions, difficulty, and topics in real-time based on the candidate's answers. Built with a hybrid Edge-Cloud LLM architecture utilizing a local Small Language Model (SLM) for drafting and the Gemini API for strategic evaluation.

---

## ✨ Features

- **Hybrid Edge-Cloud Architecture**: Combines local Phi-3 SLM (via Llama.cpp) and cloud-based Gemini API.
- **Dynamic Difficulty & Pivoting**: Automatically detects knowledge gaps, hesitation patterns, and performance trend signals to adjust difficulty or pivot sub-topics.
- **Real-Time Badges**: Displays immediate feedback (e.g., *Good Answer*, *Vague*, *Incorrect*, *Hesitation*) as the candidate responds.
- **Rich Analytics Dashboard**: Renders interactive Plotly charts showing score trends, answer quality distribution, and personalized qualitative AI feedback.
- **Natural Tone Enforcement**: Automatically monitors and filters robotic transitions to keep the dialogue conversational and human-like.

---

## 🛠️ Tech Stack

- **Frontend**: Streamlit (Glassmorphism dark theme)
- **Backend Orchestrator**: Python (`google-generativeai`, `llama-cpp-python`)
- **Performance Analysis**: Plotly
- **Models**:
  - Cloud: Gemini 2.5 Flash Lite
  - Edge: Phi-3-Interview-Merged 3.8B (GGUF format)

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
Create a `.env` file in the root directory and add your Google API key:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 4. Download the GGUF Model
Because the 7.6GB Small Language Model file (`*.gguf`) is too large for GitHub, it is excluded via `.gitignore`. 
- Download your merged Phi-3 model file (`Phi3_Interview_Merged-3.8B-F16-001-001.gguf` or similar).
- Place the `.gguf` file in the **root** of the project directory.
- Update the filename path in `interview.py` (around line 19) if needed:
  ```python
  SLM_MODEL_PATH = "Phi3_Interview_Merged-3.8B-F16-001-001.gguf"
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
