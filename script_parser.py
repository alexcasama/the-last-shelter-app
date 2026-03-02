"""
Script Parser — Converts a user-written .md script into structured sections.

Parses the markdown format:
- ## INTRO (timestamps)
- ## PHASE N: TITLE (timestamps | duration)
- ## JACK BREAK #N: TITLE (timestamps | duration)
- ## OUTRO

For each section, extracts:
- type: "intro", "phase", "jack_break", "outro"
- title, number, timestamps, duration
- stage_directions: [BRACKET TEXT] strings
- clean_text: narration without stage directions
- speaker: "jack" or "narrator"
- day_markers: [DAY X] references
"""

import re
import json
from story_engine import generate_json, GEMINI_MODEL_FLASH


def parse_script(raw_md: str) -> dict:
    """
    Parse a raw .md script into structured sections.
    
    Returns:
        {
            "title": str,
            "total_duration": str,
            "sections": [...],
            "characters": [...],
            "objects": [...]
        }
    """
    lines = raw_md.split("\n")
    
    # Extract title from first H1
    title = ""
    subtitle = ""
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
        elif line.startswith("## Complete Script") or line.startswith("## Complete script"):
            subtitle = line[3:].strip()
            break
    
    # Extract total duration from subtitle
    total_duration = ""
    dur_match = re.search(r'(\d+)\s*[Mm]inutes?', subtitle)
    if dur_match:
        total_duration = f"{dur_match.group(1)} min"
    
    # Split into sections by ## headers
    sections = []
    current_section = None
    current_lines = []
    
    for line in lines:
        # Detect section headers with or without '## ' prefix
        # Allowed headers: INTRO, OUTRO, PHASE X, CHAPTER X, JACK BREAK
        is_header = False
        header_text = ""
        
        # Check standard markdown format
        md_match = re.match(r'^##\s+(.+)$', line)
        if md_match and not line.startswith("## Complete"):
            is_header = True
            header_text = md_match.group(1).strip()
            
        # Check plain text headers (from PDF extraction)
        elif re.match(r'^(?:INTRO|OUTRO|PHASE\s+\d+|CHAPTER\s+\d+|JACK\s+BREAK.*)(?:\s*\(.*?\))?(?:\s*:.*)?$', line.strip(), re.IGNORECASE):
            is_header = True
            header_text = line.strip()
            
        if is_header:
            # Save previous section
            if current_section is not None:
                current_section["raw_body"] = "\n".join(current_lines).strip()
                sections.append(current_section)
            
            current_section = _parse_section_header(header_text)
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)
    
    # Save last section
    if current_section is not None:
        current_section["raw_body"] = "\n".join(current_lines).strip()
        sections.append(current_section)
    
    # Process each section's body
    for section in sections:
        _process_section_body(section)
        del section["raw_body"]  # Remove raw body after processing
    
    # Calculate total word count (narration only)
    word_count = 0
    for section in sections:
        clean = section.get("clean_text", "")
        if clean:
            word_count += len(clean.split())
    
    # Extract characters and objects intelligently using LLM
    full_text = raw_md
    extracted = _extract_entities_with_llm(full_text)
    characters = extracted.get("characters", [])
    objects = extracted.get("objects", [])
    
    return {
        "title": title,
        "total_duration": total_duration,
        "word_count": word_count,
        "sections": sections,
        "characters": characters,
        "objects": objects,
    }


def _parse_section_header(header: str) -> dict:
    """Parse a section header like 'PHASE 1: ARRIVAL AND DEVASTATION (1:30-3:30 | 2 min)'."""
    
    section = {
        "type": "unknown",
        "title": header,
        "number": None,
        "timestamps": None,
        "duration": None,
    }
    
    # Extract timestamps and duration in parentheses: (1:30-3:30 | 2 min)
    ts_match = re.search(r'\(([^)]+)\)', header)
    if ts_match:
        ts_content = ts_match.group(1)
        header_clean = header[:ts_match.start()].strip()
        
        # Parse timestamp range: 1:30-3:30
        time_match = re.search(r'(\d+:\d+)\s*-\s*(\d+:\d+)', ts_content)
        if time_match:
            section["timestamps"] = {
                "start": time_match.group(1),
                "end": time_match.group(2),
            }
        
        # Parse duration: 2 min, 30 sec, 6:30 min
        dur_match = re.search(r'\|\s*(.+)$', ts_content)
        if dur_match:
            section["duration"] = dur_match.group(1).strip()
    else:
        header_clean = header.strip()
    
    # Determine type
    if re.match(r'INTRO', header_clean, re.IGNORECASE):
        section["type"] = "intro"
        section["title"] = "Introduction"
    elif re.match(r'OUTRO', header_clean, re.IGNORECASE):
        section["type"] = "outro"
        section["title"] = "Outro"
    elif re.match(r'(?:PHASE|CHAPTER)\s+(\d+)', header_clean, re.IGNORECASE):
        m = re.match(r'(?:PHASE|CHAPTER)\s+(\d+)\s*:\s*(.*)', header_clean, re.IGNORECASE)
        section["type"] = "phase"
        section["number"] = int(m.group(1)) if m else None
        section["title"] = m.group(2).strip().title() if m and m.group(2) else header_clean
    elif re.match(r'JACK\s+BREAK', header_clean, re.IGNORECASE):
        m = re.match(r'JACK\s+BREAK\s*#?(\d+)\s*:\s*(.*)', header_clean, re.IGNORECASE)
        section["type"] = "jack_break"
        section["number"] = int(m.group(1)) if m else None
        section["title"] = m.group(2).strip().title() if m and m.group(2) else header_clean
    
    return section


def _process_section_body(section: dict):
    """Process the raw body text to extract clean text, stage directions, day markers."""
    raw = section.get("raw_body", "")
    
    # Remove horizontal rules
    raw = re.sub(r'^---+\s*$', '', raw, flags=re.MULTILINE)
    
    # Extract stage directions [ANYTHING IN BRACKETS]
    stage_directions = re.findall(r'\[([^\]]+)\]', raw)
    
    # Separate day markers from scene/camera directions
    day_markers = []
    camera_directions = []
    for sd in stage_directions:
        if re.match(r'DAY\s+\d', sd, re.IGNORECASE):
            day_markers.append(sd)
        else:
            camera_directions.append(sd)
    
    # Create clean text: remove all [BRACKET] lines and **JACK** speaker tags
    clean_lines = []
    skip_empty = False
    
    for line in raw.split("\n"):
        stripped = line.strip()
        
        # Skip lines that are ONLY a stage direction
        if re.match(r'^\[.+\]\s*$', stripped):
            skip_empty = True
            continue
        
        # Skip horizontal rules
        if re.match(r'^---+$', stripped):
            continue
        
        # Skip empty lines after removed content (avoid double spacing)
        if not stripped and skip_empty:
            skip_empty = False
            continue
        
        skip_empty = False
        
        # Remove inline stage directions from text
        cleaned = re.sub(r'\[([^\]]+)\]\s*', '', line)
        
        # Remove **JACK** or **JACK:** speaker tags (colon may be inside or outside bold)
        cleaned = re.sub(r'\*\*JACK:?\*\*\s*\(.*?\)\s*:?\s*', '', cleaned)
        cleaned = re.sub(r'\*\*JACK:?\*\*\s*:?\s*', '', cleaned)
        
        # Remove surrounding quotes from dialog
        cleaned_stripped = cleaned.strip()
        if cleaned_stripped.startswith('"') and cleaned_stripped.endswith('"'):
            cleaned = cleaned.replace(cleaned_stripped, cleaned_stripped[1:-1])
        # Also remove quotes that span across lines (opening quote at start)
        elif cleaned_stripped.startswith('"'):
            cleaned = cleaned.replace(cleaned_stripped, cleaned_stripped[1:], 1)
        elif cleaned_stripped.endswith('"'):
            cleaned = cleaned.replace(cleaned_stripped, cleaned_stripped[:-1], 1)
        
        # Only add non-empty lines (or preserve paragraph breaks)
        if cleaned.strip() or (clean_lines and clean_lines[-1].strip()):
            clean_lines.append(cleaned)
    
    # Clean up: remove leading/trailing empty lines
    clean_text = "\n".join(clean_lines).strip()
    
    # Remove any remaining multiple blank lines
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    
    # Determine speaker
    if section["type"] in ("intro", "jack_break", "outro"):
        speaker = "jack"
    else:
        speaker = "narrator"
    
    section["stage_directions"] = camera_directions
    section["day_markers"] = day_markers
    section["clean_text"] = clean_text
    section["speaker"] = speaker


def _extract_entities_with_llm(text: str) -> dict:
    """
    Use Gemini to intelligently extract characters and key objects from the script text.
    This replaces the legacy regex-based extraction.
    """
    # Truncate text if too long to save tokens, though usually scripts are short enough
    # If the script is huge, we grab the first 15000 chars as it usually has all characters
    truncated_text = text[:15000]
    
    prompt = f"""You are a story analyst. Read this script and extract exactly two lists of entities.

SCRIPT TEXT:
{truncated_text}

═══ EXTRACT THE FOLLOWING ═══
Analyze the script deeply and return a JSON with this EXACT structure:

{{
    "characters": [
        {{
            "name": "Full name or Role (e.g. Jack, Matt, Pilot, Uncle)",
            "type": "character or animal or family",
            "mentions": <integer, estimated importance/mentions>
        }}
    ],
    "objects": [
        {{
            "id": "lowercase_id",
            "name": "Display Name (e.g. Helicopter, Plane, Chainsaw, Pick-up Truck)",
            "mentions": <integer, estimated importance/mentions>
        }}
    ]
}}

RULES:
- "characters" should include human performers, family roles, and significant animals (like wolves, dogs).
- "objects" should ONLY include large, narratively significant mechanical or structural objects (e.g. Plane, Snow Shelter, Cabin, Truck). Do not include small hand tools unless critical to the plot.
- Estimate "mentions" based on their significance to the story (1-20+).
"""
    
    try:
        print("[Parser] Running intelligent LLM extraction for entities...")
        result = generate_json(prompt, temperature=0.2, model=GEMINI_MODEL_FLASH)
        print(f"[Parser] LLM returned keys: {list(result.keys())}")
        return {
            "characters": result.get("characters", []),
            "objects": result.get("objects", [])
        }
    except Exception as e:
        import traceback
        print(f"[Parser] LLM extraction failed: {e}")
        traceback.print_exc()
        return {"characters": [], "objects": []}



# Quick test when run directly
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            raw = f.read()
        result = parse_script(raw)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python script_parser.py <script.md>")
