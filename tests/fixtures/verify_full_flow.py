"""
verify_full_e2e_flow.py - Executes the complete real backend flow:
1. Register new user
2. Onboard candidate profile
3. Start interview session in "Python Programming"
4. Answer Turn 1
5. Answer Turn 2
6. Answer Turn 3
7. End interview session & verify summary
8. Fetch session history
9. Fetch analytics summary & trends
10. Delete user data (GDPR) and verify account removal
"""

import os
import sys
import shutil
import sqlite3

sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from backend.main import app
import database

TEST_DB = "verify_e2e.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

# Copy baseline schema to test DB
database.init_db(TEST_DB)
app.state.db_path = TEST_DB

client = TestClient(app)

print("=== STARTING FULL END-TO-END FLOW VERIFICATION ===")

# 1. Register
print("\n[Step 1] Register new user...")
reg_res = client.post(
    "/api/auth/register",
    json={
        "email": "candidate_bekon@test.com",
        "password": "Password123!",
        "full_name": "Bekon Candidate"
    }
)
assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
user_data = reg_res.json()
print("Registered:", user_data["user"]["email"], "user_id:", user_data["user"]["user_id"])
csrf_token = reg_res.cookies.get("csrf_token")
headers = {"X-CSRF-Token": csrf_token}

# 2. Onboarding Profile
print("\n[Step 2] Candidate Onboarding Profile Setup...")
prof_res = client.put(
    "/api/profile",
    headers=headers,
    json={
        "full_name": "Bekon Candidate",
        "college_org": "Bekon Institute",
        "target_role": "Software Engineer",
        "year_experience": "1-3",
        "preferred_domains": ["Python Programming"],
        "consent_save_sessions": True
    }
)
assert prof_res.status_code == 200, f"Profile setup failed: {prof_res.text}"
print("Profile updated successfully:", prof_res.json())

# 3. Start Interview
print("\n[Step 3] Starting Python Programming interview...")
start_res = client.post(
    "/api/interviews/start",
    headers=headers,
    json={"domain": "Python Programming"}
)
assert start_res.status_code == 201, f"Start failed: {start_res.text}"
start_data = start_res.json()
session_id = start_data["session_id"]
print(f"Session #{session_id} started. Initial Question:\n\"{start_data['question']}\"")

# 4. Turn 1 Answer
print("\n[Step 4] Submitting Turn 1 answer...")
t1_res = client.post(
    f"/api/interviews/{session_id}/answer",
    headers=headers,
    json={"answer": "Lists are mutable sequences stored in dynamic contiguous arrays, while tuples are immutable fixed-size sequences with lower memory overhead."}
)
assert t1_res.status_code == 200, f"Turn 1 failed: {t1_res.text}"
t1_data = t1_res.json()
print(f"Turn 1 evaluated - Score: {t1_data['score']}/10, Classification: {t1_data['label']}")
print(f"Follow-up Question:\n\"{t1_data['interviewer_message']}\"")

# 5. Turn 2 Answer
print("\n[Step 5] Submitting Turn 2 answer...")
t2_res = client.post(
    f"/api/interviews/{session_id}/answer",
    headers=headers,
    json={"answer": "Generators compute values lazily using the yield statement, maintaining state with frame objects, while standard iterables store the full collection in memory."}
)
assert t2_res.status_code == 200, f"Turn 2 failed: {t2_res.text}"
t2_data = t2_res.json()
print(f"Turn 2 evaluated - Score: {t2_data['score']}/10, Classification: {t2_data['label']}")
print(f"Follow-up Question:\n\"{t2_data['interviewer_message']}\"")

# 6. Turn 3 Answer
print("\n[Step 6] Submitting Turn 3 answer...")
t3_res = client.post(
    f"/api/interviews/{session_id}/answer",
    headers=headers,
    json={"answer": "The GIL is a mutex that prevents multiple native threads from executing Python bytecodes simultaneously, ensuring thread-safe reference counting."}
)
assert t3_res.status_code == 200, f"Turn 3 failed: {t3_res.text}"
t3_data = t3_res.json()
print(f"Turn 3 evaluated - Score: {t3_data['score']}/10, Classification: {t3_data['label']}")

# 7. End Interview
print("\n[Step 7] Ending interview session...")
end_res = client.post(
    f"/api/interviews/{session_id}/end",
    headers=headers
)
assert end_res.status_code == 200, f"End failed: {end_res.text}"
detail_res = client.get(f"/api/interviews/{session_id}")
assert detail_res.status_code == 200
detail_data = detail_res.json()
print(f"Session finalized. Overall Score: {detail_data['session']['overall_score']}/10, Status: {detail_data['status']}")
print(f"Final Summary Items ({len(detail_data['final_summary_items'])} items):")
for item in detail_data['final_summary_items']:
    print(f"  - [{item['category'].upper()}] {item['title']}: {item['text']}")

# 8. History
print("\n[Step 8] Fetching interview history...")
hist_res = client.get("/api/interviews/history")
assert hist_res.status_code == 200
hist_data = hist_res.json()
sessions = hist_data if isinstance(hist_data, list) else hist_data.get("sessions", [])
print(f"History contains {len(sessions)} sessions. First session domain: {sessions[0]['domain']}")

# 9. Analytics
print("\n[Step 9] Fetching candidate analytics...")
summary_res = client.get("/api/analytics/summary")
assert summary_res.status_code == 200
sum_data = summary_res.json()
print(f"Candidate Summary: Total Sessions = {sum_data['total_sessions']}, Avg Score = {sum_data['avg_score']}")

# 10. Delete Data (GDPR)
print("\n[Step 10] Testing GDPR irreversible data deletion...")
del_res = client.request(
    "DELETE",
    "/api/settings/data",
    headers=headers,
    json={"confirmation": "DELETE MY DATA"}
)
assert del_res.status_code == 200, f"Deletion failed: {del_res.text}"
print("Data deletion response:", del_res.json()["message"])

# Confirm login fails afterward
login_check = client.post(
    "/api/auth/login",
    json={"email": "candidate_bekon@test.com", "password": "Password123!"}
)
assert login_check.status_code == 401, f"Expected 401 login failure after deletion, got {login_check.status_code}"
print("Confirmed: Login fails after deletion (account successfully wiped).")

# Clean up test DB
try:
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
except Exception:
    pass

print("\n=== FULL E2E FLOW VERIFICATION PASSED 100% GREEN ===")
