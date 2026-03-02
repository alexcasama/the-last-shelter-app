import os
import json
import traceback
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

import story_engine

with open("projects/60fb2ed6-he-built-an-incredible-log-cab/script.json", "r") as f:
    script_data = json.load(f)

def callback(msg, type):
    print(f"[{type}] {msg}")

try:
    print("Starting audit test...")
    res = story_engine.audit_survival_knowledge(script_data, callback)
    print(f"Audit Result: {json.dumps(res, indent=2)}")
except Exception as e:
    traceback.print_exc()

