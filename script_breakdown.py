"""
Script Breakdown — Extract structured metadata from a parsed script.

Uses Gemini to analyze the script text and extract:
- Character details (name, age, physical description, motivation)
- Location information
- Construction/project details
- Timeline
- Conflicts
- Narrative arcs with tension values

Also converts parsed script sections → narration.json format (deterministic, no AI).
"""

import json
import re
from story_engine import generate_json, GEMINI_MODEL_FLASH


def extract_metadata(script_data: dict, progress_callback=None) -> dict:
    """
    Use Gemini to extract structured story metadata from the parsed script.
    
    Args:
        script_data: Parsed script dict from script_parser.py
        progress_callback: Optional callback(message, type)
    
    Returns:
        story.json-compatible dict
    """
    if progress_callback:
        progress_callback("🔍 Analyzing script for characters, location, and story structure...", "info")
    
    # Build full text from sections
    sections_text = ""
    for s in script_data.get("sections", []):
        label = s.get("title", s.get("type", ""))
        speaker = s.get("speaker", "narrator")
        text = s.get("clean_text", "")
        ts = ""
        if s.get("timestamps"):
            ts = f" ({s['timestamps']['start']}-{s['timestamps']['end']})"
        sections_text += f"\n\n### {s.get('type', '').upper()}: {label}{ts}\n[Speaker: {speaker}]\n{text}"
    
    # Characters already detected by parser
    parser_chars = script_data.get("characters", [])
    parser_chars_text = ", ".join([f"{c['name']} ({c.get('type', 'character')})" for c in parser_chars])
    
    prompt = f"""You are a story analyst. Read this complete narration script and extract structured metadata.

The script is for a documentary-style YouTube survival/construction show called "The Last Shelter".

PARSED CHARACTERS DETECTED: {parser_chars_text}
TOTAL DURATION: {script_data.get('total_duration', 'unknown')}
WORD COUNT: {script_data.get('word_count', 0)}

FULL SCRIPT:
{sections_text}

═══ EXTRACT THE FOLLOWING ═══

Analyze the script deeply and return a JSON with this EXACT structure:

{{
    "title": "The episode title as found in the script",
    "synopsis": "2-3 sentences Netflix-style. Hook the reader, reveal the stakes, NOT the outcome.",
    "duration_minutes": <integer, estimated from timestamps or word count>,
    "episode_type": "<build|rescue|restore|survive|full_build>",
    
    "character": {{
        "name": "Protagonist full name",
        "age": "estimated age or range",
        "physical_description": "Detailed physical appearance: height, build, skin tone, hair, facial hair, clothing style. Be specific enough for image generation.",
        "motivation": "What drives them — their emotional core",
        "internal_voice": "A quote that captures their mindset",
        "meaningful_object": "An object with emotional significance",
        "companion": {{
            "name": "Animal companion name or null",
            "breed": "Breed/type or null",
            "role": "Brief role description or null"
        }}
    }},
    
    "location": {{
        "name": "Specific location name",
        "region": "Broader region",
        "terrain": "Terrain type",
        "climate": "Climate description",
        "nearest_town": "Nearest civilization reference"
    }},
    
    "construction": {{
        "type": "What is being built/restored",
        "materials": "Primary materials used",
        "scale": "Size/scope of the project",
        "unique_challenge": "What makes this build particularly difficult"
    }},
    
    "timeline": {{
        "total_days": <integer, total days of the story>,
        "season": "Time of year",
        "deadline_pressure": "Why there's a time limit"
    }},
    
    "conflicts": [
        {{
            "day": <integer or estimate>,
            "title": "Short concrete title (e.g. 'Unexpected Storm', 'Broken Foundation')",
            "description": "1 sentence describing the conflict",
            "severity": <1-10>
        }}
    ],
    
    "narrative_arcs": [
        {{
            "phase": "Chapter title from the script",
            "percentage": <integer, % of total duration>,
            "tension": <0-100, narrative tension level>,
            "description": "1-2 sentences of what the viewer sees",
            "day_range": "e.g. 'Days 1-5' or null"
        }}
    ],
    
    "el_momento": "The most emotionally powerful moment in the story — describe it in one vivid sentence"
}}

RULES:
- narrative_arcs should correspond to the CHAPTER sections in the script (phases), NOT breaks
- Each chapter = one narrative_arc entry
- Percentages must add up to 100
- Tension should follow a realistic narrative curve (rising with spikes at conflict points)
- If companion info is missing/not applicable, set to null
- Be extremely specific with physical_description — it will be used for image generation
"""

    if progress_callback:
        progress_callback("🧠 Gemini analyzing script structure...", "info")
    
    story = generate_json(prompt, temperature=0.3, max_tokens=8000, model=GEMINI_MODEL_FLASH)
    
    if progress_callback:
        char_name = story.get("character", {}).get("name", "Unknown")
        location = story.get("location", {}).get("name", "Unknown")
        arcs = len(story.get("narrative_arcs", []))
        conflicts = len(story.get("conflicts", []))
        progress_callback(f"✅ Metadata extracted: {char_name} in {location}, {arcs} arcs, {conflicts} conflicts", "success")
    
    return story


def build_narration(script_data: dict, progress_callback=None) -> dict:
    """
    Convert parsed script sections → narration.json format (deterministic, no AI).
    
    Maps:
    - intro section → narration.intro
    - phase sections → narration.phases
    - jack_break sections → narration.breaks
    - outro section → narration.close
    
    Args:
        script_data: Parsed script dict
        progress_callback: Optional callback
    
    Returns:
        narration.json-compatible dict
    """
    if progress_callback:
        progress_callback("📝 Building narration from script sections...", "info")
    
    sections = script_data.get("sections", [])
    
    intro = {}
    phases = []
    breaks = []
    close = {}
    
    for section in sections:
        stype = section.get("type", "")
        text = section.get("clean_text", "")
        word_count = len(text.split()) if text else 0
        
        # Parse duration to seconds
        duration_secs = _parse_duration_to_seconds(section.get("duration", ""))
        
        if stype == "intro":
            intro = {
                "text": text,
                "duration_seconds": duration_secs or 90,
                "word_count": word_count,
            }
        
        elif stype == "phase":
            phases.append({
                "phase_name": section.get("title", f"Phase {section.get('number', '?')}"),
                "chapter": section.get("title", f"Phase {section.get('number', '?')}"),
                "narration": text,
                "narration_text": text,
                "word_count": word_count,
                "duration_seconds": duration_secs,
                "day_markers": section.get("day_markers", []),
                "timestamps": section.get("timestamps"),
            })
        
        elif stype == "jack_break":
            breaks.append({
                "title": section.get("title", f"Break {section.get('number', '?')}"),
                "text": text,
                "duration_seconds": duration_secs or 30,
                "word_count": word_count,
            })
        
        elif stype == "outro":
            # Split into close text and teaser if possible
            teaser = ""
            close_text = text
            # Check if there's a "Next time" or similar line
            teaser_match = re.search(r'(?:Next time|Next episode|Coming up).*', text, re.IGNORECASE | re.DOTALL)
            if teaser_match:
                teaser = teaser_match.group(0).strip()
                close_text = text[:teaser_match.start()].strip()
            
            close = {
                "text": close_text,
                "teaser": teaser,
                "duration_seconds": duration_secs or 35,
                "word_count": word_count,
            }
    
    # Calculate totals
    voiceover_words = sum(p.get("word_count", 0) for p in phases)
    breaks_words = sum(b.get("word_count", 0) for b in breaks)
    intro_words = intro.get("word_count", 0)
    close_words = close.get("word_count", 0)
    total_words = voiceover_words + breaks_words + intro_words + close_words
    
    narration = {
        "intro": intro,
        "phases": phases,
        "breaks": breaks,
        "close": close,
        "summary": {
            "total_words": total_words,
            "voiceover_words": voiceover_words,
            "breaks_words": breaks_words + intro_words + close_words,
            "phases_count": len(phases),
            "breaks_count": len(breaks),
            "chapters_count": len(phases),
        }
    }
    
    if progress_callback:
        progress_callback(
            f"✅ Narration built: {total_words} words, {len(phases)} phases, {len(breaks)} breaks",
            "success"
        )
    
    return narration


def _parse_duration_to_seconds(duration_str: str) -> int:
    """Parse duration strings like '2 min', '30 sec', '6:30 min' to seconds."""
    if not duration_str:
        return 0
    
    # "X:XX min" format
    m = re.match(r'(\d+):(\d+)\s*min', duration_str)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    
    # "X min" format
    m = re.match(r'(\d+)\s*min', duration_str)
    if m:
        return int(m.group(1)) * 60
    
    # "X sec" format
    m = re.match(r'(\d+)\s*sec', duration_str)
    if m:
        return int(m.group(1))
    
    return 0
