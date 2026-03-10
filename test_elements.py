import json
from pathlib import Path
from story_engine import analyze_elements

project_dir = Path("projects/571e1a67-his-plane-crashed-in-the-arcti")

with open(project_dir / "story.json") as f:
    story = json.load(f)
with open(project_dir / "narration.json") as f:
    narration = json.load(f)
with open(project_dir / "script.json") as f:
    script_data = json.load(f)

def dummy_callback(msg, msg_type):
    print(f"[{msg_type}] {msg}")

elements = analyze_elements(story, narration, script_data, progress_callback=dummy_callback)

print("\n\nFINAL ELEMENTS LIST:")
for e in elements:
    print(f"- [{e.get('category')}] {e.get('label')} (ID: {e.get('id')})")
    print(f"  Frontal Prompt: {e.get('frontal_prompt')}")
    print()
