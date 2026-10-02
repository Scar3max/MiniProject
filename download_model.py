import os
import sys
from huggingface_hub import hf_hub_download

MODEL_FILE = "qwen_interview_q4_k_m.gguf"
REPO_ID = os.getenv("HF_MODEL_REPO", "your-username/qwen-interview-slm")
HF_TOKEN = os.getenv("HF_TOKEN", None) # Only needed if repo is private

if not os.path.exists(MODEL_FILE):
    print(f"📥 Downloading {MODEL_FILE} from Hugging Face ({REPO_ID})...")
    try:
        downloaded_path = hf_hub_download(
            repo_id=REPO_ID,
            filename=MODEL_FILE,
            local_dir=".",
            token=HF_TOKEN
        )
        print(f"✅ Model downloaded successfully to {downloaded_path}")
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        sys.exit(1)
else:
    print(f"✅ Model file {MODEL_FILE} already present.")