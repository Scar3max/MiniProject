import sys
import os

# Set testing environment variable
os.environ["TESTING"] = "1"

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
