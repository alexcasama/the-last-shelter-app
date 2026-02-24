import json
import glob
from pathlib import Path

def fix_prompts(filepath):
    print(f"Fixing {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    modified = False
    
    # Depending on the structure, it might be a dict with "storyboard" list
    if isinstance(data, dict) and "storyboard" in data:
        scenes = data["storyboard"]
    elif isinstance(data, list):
        scenes = data
    else:
        print("Unknown format")
        return
        
    for scene in scenes:
        prompt_data = scene.get("prompt", {})
        if not prompt_data:
            continue
            
        locations = prompt_data.get("locations", [])
        prompt_text = prompt_data.get("prompt_text", "")
        
        # If there is only ONE location image, replace @Image1 with @Image
        if len(locations) == 1 and "@Image1" in prompt_text and "@Image2" not in prompt_text:
            new_text = prompt_text.replace("@Image1", "@Image")
            prompt_data["prompt_text"] = new_text
            modified = True
            print(f"  Fixed scene {scene.get('scene_number')}")
            
    if modified:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {filepath}")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    project_dir = "/Users/alexkasama/wa-imagenes-3/the-last-shelter/projects/60fb2ed6-he-built-an-incredible-log-cab"
    
    # Find all storyboard.json files
    for file in glob.glob(f"{project_dir}/production/**/storyboard.json", recursive=True):
        fix_prompts(file)
