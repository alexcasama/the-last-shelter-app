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
        # Detect section headers (## INTRO, ## PHASE, ## JACK BREAK, ## OUTRO)
        section_match = re.match(r'^##\s+(.+)$', line)
        if section_match and not line.startswith("## Complete"):
            # Save previous section
            if current_section is not None:
                current_section["raw_body"] = "\n".join(current_lines).strip()
                sections.append(current_section)
            
            header = section_match.group(1).strip()
            current_section = _parse_section_header(header)
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
    
    # Extract characters and objects
    full_text = raw_md
    characters = _extract_characters(full_text)
    objects = _extract_objects(full_text)
    
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
    elif re.match(r'PHASE\s+(\d+)', header_clean, re.IGNORECASE):
        m = re.match(r'PHASE\s+(\d+)\s*:\s*(.*)', header_clean, re.IGNORECASE)
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


def _extract_characters(text: str) -> list:
    """Extract recognizable characters from the full script text."""
    characters = []
    
    # Common patterns for character identification
    # Look for names that appear multiple times in action context
    # We focus on proper nouns that are actors in the story
    
    # Find named characters: words that appear as subjects doing actions
    # Pattern: "Name verb..." or "Name's"
    name_pattern = re.compile(r'\b([A-Z][a-z]+)\b')
    name_counts = {}
    
    # Common non-character words to exclude
    exclude = {
        'The', 'This', 'That', 'But', 'And', 'Now', 'When', 'Then',
        'His', 'Her', 'He', 'She', 'It', 'They', 'We', 'You', 'In',
        'On', 'At', 'To', 'For', 'By', 'Is', 'Are', 'Was', 'Were',
        'Has', 'Had', 'Can', 'Will', 'Would', 'Could', 'Should',
        'Day', 'Days', 'Not', 'No', 'Yes', 'If', 'Or', 'So',
        'Just', 'Only', 'Even', 'Still', 'Yet', 'All', 'Each',
        'Every', 'One', 'Two', 'Three', 'Four', 'Five', 'Over',
        'About', 'Into', 'From', 'With', 'After', 'Before', 'During',
        'Between', 'Under', 'Until', 'Without', 'Nothing', 'Everything',
        'Something', 'Here', 'There', 'Where', 'How', 'What', 'Why',
        'Who', 'Whose', 'Which', 'Much', 'Many', 'More', 'Most',
        'First', 'Last', 'Next', 'Phase', 'Break', 'Jack', 'Complete',
        'Script', 'Minutes', 'Intro', 'Outro', 'Cut', 'Zoom',
        'Aerial', 'Epic', 'Brutal', 'Temperature', 'Temperatures',
        'Wind', 'Snow', 'Winter', 'Ninety', 'Fifteen', 'Twenty',
        'Thirty', 'Forty', 'Fifty', 'Sixty', 'Finally', 'Suddenly',
        'Outside', 'Inside', 'Behind', 'Beside', 'Also', 'Very',
        'Almost', 'Already', 'Enough',        'JACK', 'BUILT', 'INCREDIBLE',
        'LOG', 'CABIN', 'ALONE', 'BEFORE', 'WINTER', 'HELICOPTER',
        'FLYING', 'LOOKING', 'STANDING', 'POINTING',
        # Geographic names that appear as proper nouns
        'Yukon', 'Alaska', 'Siberia', 'Montana', 'Colorado', 'Maine',
        'Quebec', 'Scandinavia', 'Norway', 'Sweden', 'Finland', 'Iceland',
        'Scotland', 'Patagonia', 'Ford', 'Whitehorse', 'Dawson',
        'Fairbanks', 'Denali', 'America', 'Canada', 'Russia',
        'Stockholm', 'Alone', 'Hatchet', 'Wild',
    }
    
    for match in name_pattern.finditer(text):
        name = match.group(1)
        if name not in exclude and len(name) > 2:
            name_counts[name] = name_counts.get(name, 0) + 1
    
    # Characters are names that appear 3+ times (significant presence)
    for name, count in sorted(name_counts.items(), key=lambda x: -x[1]):
        if count >= 3:
            char_type = "character"
            # Detect if it's an animal name (often the dog)
            # Check context around the name for animal indicators
            animal_check = re.search(
                rf'{name}\s+(?:jumps|curls|presses|barks|whines|howls|sniffs|wags)',
                text, re.IGNORECASE
            )
            if animal_check:
                char_type = "animal"
            
            characters.append({
                "name": name,
                "type": char_type,
                "mentions": count,
            })
    
    # Also detect Jack (the presenter) — always present
    jack_present = bool(re.search(r'\*\*JACK:?\*\*', text))
    if jack_present and not any(c["name"] == "Jack" for c in characters):
        characters.insert(0, {
            "name": "Jack",
            "type": "presenter",
            "mentions": len(re.findall(r'\*\*JACK:?\*\*', text)),
        })
    
    # Detect relationship-based characters (uncle, father, brother, etc.)
    relationships = {
        'uncle': r'\b(?:uncle|his uncle|the uncle)\b',
        'father': r'\b(?:father|his father|the father|his dad)\b',
        'mother': r'\b(?:mother|his mother|the mother|his mom)\b',
        'brother': r'\b(?:brother|his brother|the brother)\b',
        'sister': r'\b(?:sister|his sister|the sister)\b',
        'wife': r'\b(?:wife|his wife|the wife)\b',
        'grandfather': r'\b(?:grandfather|his grandfather|grandpa)\b',
    }
    
    for rel_type, pattern in relationships.items():
        rel_matches = re.findall(pattern, text, re.IGNORECASE)
        if len(rel_matches) >= 1:
            # Try to find the actual name nearby: "His uncle [Name]" or "named [Name]"
            name_nearby = re.search(
                rf'(?:uncle|father|mother|brother|sister|wife|grandfather)\s+([A-Z][a-z]+)',
                text
            )
            # Also check if there's a named character earlier: "Name ... his uncle"
            if name_nearby:
                rel_name = name_nearby.group(1)
                display = f"{rel_name} ({rel_type})"
            else:
                # Use the relationship as display if no name found
                display = rel_type.title()
                rel_name = rel_type.title()
            
            # Don't add if already in characters list
            if not any(c["name"] == rel_name for c in characters):
                characters.append({
                    "name": display,
                    "type": "family",
                    "mentions": len(rel_matches),
                })
    
    return characters


def _extract_objects(text: str) -> list:
    """
    Extract large, recognizable objects from the script.
    Only objects big enough for a Kling element (vehicles, large machines).
    NOT small hand tools (axe, chisel, saw, etc.)
    """
    objects = []
    
    # Patterns for large recognizable objects
    large_objects = {
        "pickup": r'\b(?:pickup|pick-up|truck)\b',
        "chainsaw": r'\bchainsaw\b',
        "helicopter": r'\bhelicopter\b',
        "atv": r'\b(?:ATV|atv|quad|four-wheeler)\b',
        "snowmobile": r'\bsnowmobile\b',
        "boat": r'\b(?:boat|canoe|kayak)\b',
        "cabin": r'\bcabin\b',
        "tent": r'\btent\b',
        "generator": r'\bgenerator\b',
        "wood_stove": r'\b(?:wood stove|chimney|fireplace)\b',
    }
    
    text_lower = text.lower()
    for obj_id, pattern in large_objects.items():
        matches = re.findall(pattern, text_lower)
        if len(matches) >= 2:  # Must appear at least twice to be significant
            # Get a display name from the first match in original text
            first_match = re.search(pattern, text, re.IGNORECASE)
            display_name = first_match.group(0) if first_match else obj_id
            objects.append({
                "id": obj_id,
                "name": display_name.title(),
                "mentions": len(matches),
            })
    
    return objects


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
