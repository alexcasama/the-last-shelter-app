import os
import sys
import traceback
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

print("Starting auto_research test...")
try:
    import story_engine
    print("Loaded story_engine")
    res = story_engine.auto_research_mechanics(["Building a Log Cabin"])
    print(f"Result: {res}")
except Exception as e:
    print("Exception occurred:")
    traceback.print_exc()
