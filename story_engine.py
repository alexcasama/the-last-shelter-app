"""
The Last Shelter — Story Engine
Uses Google Gemini API to generate stories and scene breakdowns.
Uses Google Imagen (Nanobanana Pro) for image generation.
"""
import os
import json
import re
import base64
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import diversity_tracker

# Google GenAI SDK
from google import genai
from google.genai import types

# Models
GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_MODEL_FLASH = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-3-pro-image-preview"

# Batch processing
SCENE_BATCH_SIZE = 50
PROMPT_BATCH_SIZE = 40
MAX_PARALLEL_BATCHES = 3

# Scene duration — each scene becomes one video clip
# Change this when switching video generation models (Veo 3 = 8s)
SECONDS_PER_SCENE = 8

# Paths
BASE_DIR = Path(__file__).parent
STORY_DNA_PATH = BASE_DIR / "docs" / "STORY_DNA.md"
SHOW_BIBLE_PATH = BASE_DIR / "docs" / "SHOW_BIBLE.md"
CONFIG_PATH = BASE_DIR / "config" / "style.json"

_client = None


def load_config():
    """Load show configuration."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_story_dna():
    """Load the STORY_DNA.md master prompt."""
    with open(STORY_DNA_PATH) as f:
        return f.read()


def load_show_bible():
    """Load the SHOW_BIBLE.md for context."""
    with open(SHOW_BIBLE_PATH) as f:
        return f.read()


def init_client():
    """Initialize the Google GenAI client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set")
        _client = genai.Client(api_key=api_key)
    return _client


def generate_text(prompt, temperature=0.7, max_tokens=30000, model=None):
    """Generate text content with Gemini."""
    client = init_client()
    model = model or GEMINI_MODEL
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    )
    return response.text


def _repair_truncated_json(text):
    """Attempt to repair truncated JSON by closing open strings, arrays, and objects."""
    if not text or not text.strip():
        return None
    
    text = text.strip()
    
    # Track state
    in_string = False
    escape_next = False
    stack = []  # track open brackets/braces
    
    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if not in_string:
            if ch in ('{', '['):
                stack.append(ch)
            elif ch == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif ch == ']' and stack and stack[-1] == '[':
                stack.pop()
    
    # Close any open string
    if in_string:
        text += '"'
    
    # Close any open brackets/braces in reverse order
    for bracket in reversed(stack):
        if bracket == '{':
            text += '}'
        elif bracket == '[':
            text += ']'
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try more aggressive repair: find last complete key-value pair
        # Remove trailing partial content after last complete value
        for end_pattern in ['"}', '"]', '},', '],']:
            last_idx = text.rfind(end_pattern)
            if last_idx > 0:
                truncated = text[:last_idx + len(end_pattern)]
                # Close remaining structure
                for bracket in reversed(stack):
                    if bracket == '{':
                        truncated += '}'
                    elif bracket == '[':
                        truncated += ']'
                try:
                    return json.loads(truncated)
                except json.JSONDecodeError:
                    continue
        return None


def generate_json(prompt, temperature=0.3, max_tokens=8000, model=None):
    """Generate JSON content with Gemini, forced JSON output."""
    client = init_client()
    model = model or GEMINI_MODEL
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
        )
    )
    
    text = response.text
    if text is None:
        # Debug: log the actual block reason
        block_reason = "unknown"
        try:
            if hasattr(response, 'candidates') and response.candidates:
                c = response.candidates[0]
                block_reason = f"finish_reason={getattr(c, 'finish_reason', '?')}"
                if hasattr(c, 'safety_ratings') and c.safety_ratings:
                    block_reason += f" safety={[(str(r.category), str(r.probability)) for r in c.safety_ratings]}"
            elif hasattr(response, 'prompt_feedback'):
                block_reason = f"prompt_feedback={response.prompt_feedback}"
        except Exception:
            pass
        print(f"[generate_json] Empty response. Block reason: {block_reason}")
        print(f"[generate_json] Prompt length: {len(prompt)} chars")
        raise ValueError(f"Gemini returned empty response. Reason: {block_reason}")
    
    # Check for truncation via finish_reason
    try:
        if hasattr(response, 'candidates') and response.candidates:
            finish_reason = getattr(response.candidates[0], 'finish_reason', None)
            if finish_reason and str(finish_reason) not in ('STOP', 'FinishReason.STOP', '1'):
                print(f"[generate_json] WARNING: finish_reason={finish_reason}, response may be truncated ({len(text)} chars)")
    except Exception:
        pass
    
    # Try normal parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        # Attempt repair on truncated JSON
        print(f"[generate_json] JSON parse failed: {e}. Attempting repair...")
        repaired = _repair_truncated_json(text)
        if repaired is not None:
            print(f"[generate_json] JSON repair successful! Salvaged {len(str(repaired))} chars")
            return repaired
        raise  # re-raise original error if repair failed


def generate_json_with_search(prompt, temperature=0.5, max_tokens=8000, model=None):
    """
    Generate JSON with Google Search grounding enabled.
    Used for retries — Gemini searches the internet for real references
    (survival stories, cabin building techniques, locations) to improve quality.
    
    NOTE: response_mime_type="application/json" is NOT compatible with
    Google Search grounding, so we extract JSON manually from the response.
    """
    client = init_client()
    model = model or GEMINI_MODEL
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )
    )
    
    text = response.text
    if text is None:
        raise ValueError("Gemini returned empty response (text is None). Possible content filter or token limit.")
    
    # Extract JSON from response — may contain markdown code fences
    text = text.strip()
    if text.startswith("```"):
        # Remove markdown code fences
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    
    return json.loads(text)


def generate_image(prompt, output_path, config=None):
    """
    Generate an image using Nanobanana Pro (gemini-3-pro-image-preview).
    
    Uses generate_content with response_modalities=['Image'].
    
    Args:
        prompt: Text prompt for image generation
        output_path: Where to save the generated image
        config: Optional config override
    
    Returns:
        Path to the saved image
    """
    client = init_client()
    cfg = config or load_config()
    
    aspect_ratio = cfg.get("image_generation", {}).get("aspect_ratio", "3:2")
    
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["Image"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            ),
        ),
    )
    
    # Extract image from response parts
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                image = part.as_image()
                image.save(output_path)
                return output_path
    
    raise Exception("No image generated — response contained no image parts")


def generate_image_with_ref(prompt, output_path, ref_image_path, config=None):
    """
    Generate an image using Nanobanana Pro with a reference image for consistency.
    
    Passes the reference image as part of contents so the model maintains
    character appearance (face, build, clothing, etc.) across generations.
    
    Args:
        prompt: Text prompt describing the new scene/pose
        output_path: Where to save the generated image
        ref_image_path: Path to the reference image to maintain consistency
        config: Optional config override
    
    Returns:
        Path to the saved image
    """
    from PIL import Image as PILImage
    
    client = init_client()
    cfg = config or load_config()
    
    aspect_ratio = cfg.get("image_generation", {}).get("aspect_ratio", "3:2")
    
    # Load reference image
    ref_img = PILImage.open(ref_image_path)
    
    # Build contents with reference image + prompt
    contents = [
        ref_img,
        prompt,
    ]
    
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["Image"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            ),
        ),
    )
    
    # Extract image from response parts
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                image = part.as_image()
                image.save(output_path)
                return output_path
    
    raise Exception("No image generated — response contained no image parts")


# =============================================================================
# QUALITY GATE — 10 Programmatic Checks
# =============================================================================

def validate_story(story):
    """
    Validate a story against the 10 rules from STORY_DNA.
    
    Returns:
        Dict with passed (bool), score (int 0-100), checks list, failed list
    """
    checks = []
    
    char = story.get("character", {})
    companion = char.get("companion", {})
    loc = story.get("location", {})
    timeline = story.get("timeline", {})
    conflicts = story.get("conflicts", [])
    el_momento = story.get("el_momento", {})
    arcs = story.get("narrative_arcs", [])
    
    # 1. Companion animal (BONUS — not required, but adds points if present and well-defined)
    has_companion = bool(companion.get("name") and (companion.get("type") or companion.get("breed")))
    checks.append({"id": 1, "name": "Companion animal (bonus)", "passed": has_companion, "bonus": True})
    
    # 2. Has deadline/timeline
    has_deadline = bool(timeline.get("total_days") and timeline.get("deadline_reason"))
    # Exception: cabin_life and full_build may not have hard deadline
    if story.get("episode_type") in ("cabin_life", "full_build") and not has_deadline:
        has_deadline = bool(timeline.get("total_days"))
    checks.append({"id": 2, "name": "Deadline/timeline exists", "passed": has_deadline})
    
    # 3. Has 3+ conflicts
    has_conflicts = len(conflicts) >= 3
    # Exception: cabin_life can have fewer
    if story.get("episode_type") == "cabin_life":
        has_conflicts = len(conflicts) >= 1
    checks.append({"id": 3, "name": "3+ escalating conflicts", "passed": has_conflicts})
    
    # 4. Conflicts escalate (days increase)
    conflicts_escalate = True
    if len(conflicts) >= 2:
        days = [c.get("day", 0) for c in conflicts]
        conflicts_escalate = all(days[i] < days[i+1] for i in range(len(days)-1))
    checks.append({"id": 4, "name": "Conflicts escalate in time", "passed": conflicts_escalate})
    
    # 5. Has EL MOMENTO
    has_momento = False
    if isinstance(el_momento, dict):
        has_momento = bool(el_momento.get("description"))
    elif isinstance(el_momento, str):
        has_momento = len(el_momento) > 10
    checks.append({"id": 5, "name": "Has EL MOMENTO", "passed": has_momento})
    
    # 6. Has meaningful object
    has_object = bool(char.get("meaningful_object") and len(str(char.get("meaningful_object", ""))) > 5)
    checks.append({"id": 6, "name": "Has meaningful object", "passed": has_object})
    
    # 7. Has internal voice
    has_voice = bool(char.get("internal_voice") and len(str(char.get("internal_voice", ""))) > 10)
    checks.append({"id": 7, "name": "Has internal voice", "passed": has_voice})
    
    # 8. Location is specific (not generic)
    loc_name = loc.get("name", "")
    has_specific_loc = bool("," in loc_name or "km" in loc_name.lower() or "miles" in loc_name.lower() or loc.get("distance_to_town_km"))
    checks.append({"id": 8, "name": "Location is specific", "passed": has_specific_loc})
    
    # 9. Narrative arcs sum ~100%
    arc_sum = sum(a.get("percentage", 0) for a in arcs)
    arcs_valid = 95 <= arc_sum <= 105 if arcs else False
    checks.append({"id": 9, "name": "Narrative arcs sum to ~100%", "passed": arcs_valid})
    
    # 10. Has humor moment
    has_humor = bool(story.get("humor_moment") and len(str(story.get("humor_moment", ""))) > 5)
    checks.append({"id": 10, "name": "Has humor moment", "passed": has_humor})
    
    passed_count = sum(1 for c in checks if c["passed"])
    # Bonus checks don't count as failures for pass/fail determination
    required_failed = [c for c in checks if not c["passed"] and not c.get("bonus")]
    all_failed = [c for c in checks if not c["passed"]]
    score = int((passed_count / len(checks)) * 100)
    
    return {
        "passed": len(required_failed) == 0,
        "score": score,
        "passed_count": passed_count,
        "total_checks": len(checks),
        "checks": checks,
        "failed": all_failed
    }


# =============================================================================
# STEP 1: STORY GENERATION (with Quality Gate + Diversity + Auto-Retry)
# =============================================================================

MAX_RETRIES = 2
MIN_STORY_STRENGTH = 80


def _build_story_prompt(story_dna, title, duration_minutes, episode_type, diversity_context="", retry_feedback=""):
    """Build the story generation prompt with all constraints."""
    prompt = f"""{story_dna}

{diversity_context}

---

GENERATE A COMPLETE STORY for the following title.
Duration: {duration_minutes} minutes.
Episode Type: {episode_type}

TITLE: "{title}"

CRITICAL RULES:
1. Follow the EXACT JSON format specified in the Story DNA above
2. The episode_type in the JSON MUST be "{episode_type}"
3. Include a "synopsis" field: 2-3 sentences, Netflix-style episode summary. Hook the reader, reveal the stakes, not the outcome.
4. The story_strength score must be honest — if any element is weak, lower the score
5. The character's physical_description must be detailed enough to generate consistent reference images
6. All temperatures must be realistic for the specified location
7. The narrative_arcs percentages must add up to 100%
8. Use the {duration_minutes}-minute structure from the Story DNA
9. If a companion animal fits the story naturally, include one with a specific name and breed. If it doesn't fit, omit it.
10. The character MUST have a meaningful_object and internal_voice
11. Include a humor_moment
12. The location name MUST be specific (include km from nearest town or a comma-separated description)
13. narrative_arcs phase names MUST be CONCRETE SURVIVAL ACTIONS that describe what the viewer literally SEES (e.g. "Log Splitting & Foundation", "Hunting in the Snow", "Making Fire", "The Blizzard Hits", "Fishing at the River", "Digging the Well", "Sealing the Roof"). Think YouTube survival channel chapters. NEVER use poetic/literary names like "Walls of Wood and Will" or "The Cold Within" or abstract terms like "Rising Action" or "Climax"
14. conflicts titles MUST be SHORT, CONCRETE survival problems (e.g. "Rotten Logs", "Blizzard", "Wolf Tracks Near Camp", "Broken Axe Handle", "Frozen Water Supply"). NEVER use poetic names like "The Silent Saw" or "The Widowmaker's Whisper"
15. Each narrative_arc phase MUST include a "tension" field (integer 0-100). The tension values form the NARRATIVE TENSION CURVE and must follow the specific pattern for the episode type:
  - build: SAWTOOTH pattern. Setup→low(15-25), progress→rising(30-50), BREAK cliffhanger→spike(70-80), crisis escalation→rising(60-75), BREAK max tension→spike(85-95), race to finish→high(75-85), resolution/"El Momento"→drop(20-35). Multiple breaks create multiple spikes.
  - rescue: DISASTER-RECOVERY. Destruction opening→high(70-85), aftermath/survey→drop(30-40), community rallies→rising(40-60), interpersonal conflicts during rebuild→spikes(65-80), race against second storm→high(80-90), "El Momento" community warmth→drop(20-30).
  - restore: MYSTERY-DISCOVERY. Arrival/discovery→medium(35-50) with curiosity, exploration reveals→rising(45-65), structural surprises (worse than expected)→spikes(60-80), restoration work→sustained(50-65), emotional discovery (letter/diary)→spike(70-85), completion/"El Momento"→drop(25-35).
  - survive: SUSTAINED HIGH. Catastrophe→instant spike(80-95), stays high throughout(70-90), brief dips during small wins(60-70) but immediately back up, final night/darkest moment→peak(90-100), dawn/rescue→sharp drop(15-25). The curve is FLAT AND HIGH, not a bell.
  - full_build: SLOW BURN. Vision/arrival→low(10-20), long construction plateau→gradual rise(25-55) over many phases, monotony/temptation to quit→dip(35-45), late technical failure→spike(70-85), final push→high(65-75), completion tour/"El Momento"→satisfying drop(20-30). Most phases in the middle range.
  - critical_system: DIAGNOSTIC RAMP. Discovery of failure→medium(40-55), diagnosis→building(50-65), fix attempt A fails→spike(70-80), fix attempt B partial→higher(75-85), conditions worsen→peak(85-95), final fix works/"El Momento"→relief drop(15-25). Tension only goes UP until the fix.
  - underground: CLAUSTROPHOBIC BUILD. Vision→low(20-30), excavation begins→rising(30-50), depth increases danger→sustained rise(50-70), collapse/flood scare→spike(80-90), completion→drop(40-50), THE REVEAL cross-section→satisfaction(25-35). The fear factor creates sharper spikes than build.
  - cabin_life: GENTLE WAVES. Morning routine→low(10-20), daily tasks→gentle rise(20-35), minor event (animal, memory)→small bump(35-50), return to routine→dip(20-30), evening reflection→emotional rise(30-45), peace moment→drop(10-20). NEVER exceeds 55. The "tension" here is emotional depth, not danger.
  Place tension spikes wherever the story demands a PRESENTER BREAK / CLIFFHANGER. Do not limit breaks to a fixed number — use as many as the story requires. Each break should feel like a chapter-ending hook.
16. narrative_arcs "description" must be 1-2 SHORT sentences max. Describe ONLY what the viewer sees happening — concrete survival action, visual detail. NEVER include "PRESENTER BREAK", cliffhanger dialogue, narration lines, or meta-commentary. Those belong in narration, not in the story structure. BAD: "PRESENTER BREAK. 'But on day 14...'" GOOD: "Day 14. Rot discovered deep inside the logs. Three days of work wasted."
17. outcome "visual" must be SHORT — 1 sentence max describing the final visual state. outcome "one_liner" must be 1 punchy sentence summarizing what happened. Keep the ENTIRE outcome block under 30 words total. BAD (too long): "An aerial drone shot pulls back from the small A-frame buried in snow. A plume of smoke..." GOOD: "The cabin stands. Smoke from the chimney. First fire burns through the night."
18. The character's profession, backstory, and reason for being in the wilderness MUST form a LOGICAL, BELIEVABLE chain. People do NOT randomly appear in remote wilderness — there is ALWAYS a concrete, real-world reason: inherited family land, a relative's property that needs help, a career in forestry/construction/military that gives them skills, a life event (divorce, retirement, job loss) that pushes them. BAD: "A graphic designer travels to Alaska to build a cabin." GOOD: "A graphic designer inherits his father's hunting land in Alaska and promises to finish the cabin his father started." The viewer must think "yes, that makes sense" — never "why would this person be here?"
19. timeline total_days MUST VARY realistically. Do NOT always use 42. Realistic ranges by type: build(21-60), rescue(3-14), restore(14-45), survive(1-7), full_build(60-120), critical_system(1-5), underground(30-90), cabin_life(1-3). Pick a number that fits the specific story and stakes.

{retry_feedback}

Return ONLY the JSON object. No markdown, no explanation."""
    return prompt


def generate_story(title, duration_minutes=20, episode_type="build", progress_callback=None, enable_variants=False):
    """
    Generate a complete story with quality gate validation and diversity constraints.
    
    Args:
        title: Episode title
        duration_minutes: Target video duration
        episode_type: Type of episode (build, rescue, restore, survive, full_build, critical_system, underground, cabin_life)
        progress_callback: Optional callback(message, type)
        enable_variants: If True, generate 2 variants and pick the best
    
    Returns:
        Tuple of (story_dict, quality_report_dict)
    """
    if enable_variants:
        return generate_story_variants(title, duration_minutes, episode_type, progress_callback)
    
    if progress_callback:
        progress_callback("📖 Loading Story DNA...", "info")
    
    story_dna = load_story_dna()
    config = load_config()
    
    # Get diversity constraints
    if progress_callback:
        progress_callback("🔍 Checking episode history for diversity...", "info")
    
    div_context = diversity_tracker.get_diversity_context()
    if div_context:
        if progress_callback:
            recs = diversity_tracker.get_recommendations()
            progress_callback(f"📊 {recs['total_episodes']} previous episodes found. Diversity constraints applied.", "info")
    
    retry_feedback = ""
    best_story = None
    best_report = None
    
    for attempt in range(1 + MAX_RETRIES):
        if progress_callback:
            if attempt == 0:
                progress_callback("🧠 Generating story with Gemini 2.5 Pro...", "info")
            else:
                progress_callback(f"🔄 Retry {attempt}/{MAX_RETRIES} — researching with Google Search + fixing issues...", "info")
        
        prompt = _build_story_prompt(story_dna, title, duration_minutes, episode_type, div_context, retry_feedback)
        
        try:
            if attempt == 0:
                # First attempt: standard generation
                story = generate_json(prompt, temperature=0.7, max_tokens=8000)
            else:
                # Retries: use Google Search grounding to research real references
                story = generate_json_with_search(prompt, temperature=0.7, max_tokens=8000)
        except Exception as e:
            print(f"[Story] Generation attempt {attempt + 1} failed: {e}")
            if progress_callback:
                progress_callback(f"❌ Attempt {attempt + 1} failed: {str(e)[:200]}", "error")
            if attempt < MAX_RETRIES:
                continue
            # If all retries failed and we have a best story, use it
            if best_story:
                break
            raise
        
        # Sanitize — Gemini may return null for nested objects
        _obj_fields = ["character", "location", "construction", "timeline", "el_momento", "outcome"]
        for field in _obj_fields:
            if story.get(field) is None:
                story[field] = {}
        # character sub-objects
        char = story.get("character", {})
        if char.get("companion") is None:
            char["companion"] = {}
        if not isinstance(story.get("conflicts"), list):
            story["conflicts"] = []
        if not isinstance(story.get("narrative_arcs"), list):
            story["narrative_arcs"] = []
        
        # Ensure core fields
        story["duration_minutes"] = duration_minutes
        story["episode_type"] = episode_type
        
        # Run quality gate
        report = validate_story(story)
        strength = story.get("story_strength", 0)
        
        if progress_callback:
            name = (story.get("character") or {}).get("name", "Unknown")
            location = (story.get("location") or {}).get("name", "Unknown")
            search_tag = " 🔍" if attempt > 0 else ""
            progress_callback(
                f"📋 Quality Gate: {report['passed_count']}/{report['total_checks']} checks passed | "
                f"Strength: {strength}/100 | {name} in {location}{search_tag}",
                "info"
            )
        
        # Check if good enough — strict pass or soft pass (7+ checks with high strength)
        strict_pass = report["passed"] and strength >= MIN_STORY_STRENGTH
        soft_pass = report["passed_count"] >= 7 and strength >= MIN_STORY_STRENGTH
        
        if strict_pass or soft_pass:
            label = "PASSED" if strict_pass else f"ACCEPTED ({report['passed_count']}/{report['total_checks']})"
            if progress_callback:
                progress_callback(f"✅ Story {label} quality gate (attempt {attempt + 1})", "success")
            best_story = story
            best_report = report
            break
        
        # Save as best so far if better than previous
        if best_report is None or report["passed_count"] > best_report["passed_count"]:
            best_story = story
            best_report = report
        
        # Build retry feedback — instruct Gemini to research real references
        if attempt < MAX_RETRIES:
            failed_names = [f["name"] for f in report["failed"]]
            retry_feedback = f"""\n\nCRITICAL: Your PREVIOUS story FAILED these quality checks: {', '.join(failed_names)}.
Story strength was {strength}/100 (minimum required: {MIN_STORY_STRENGTH}).

You now have access to Google Search. USE IT to:
- Research REAL survival stories, cabin building projects, and wilderness experiences related to "{title}"
- Find authentic details about the specific location (terrain, weather patterns, wildlife, local materials)
- Look up real techniques for the challenges in this episode type ({episode_type})
- Find genuine human stories that match the archetype to make the character more believable

Use what you find to create a MORE AUTHENTIC, DETAILED story. Fix ALL failed checks.
Do NOT repeat the same mistakes."""
            
            if progress_callback:
                progress_callback(
                    f"⚠️ Failed checks: {', '.join(failed_names)} — retrying with Google Search...",
                    "error"
                )
    
    # Final report
    if progress_callback:
        if best_report and not best_report["passed"]:
            failed_names = [f["name"] for f in best_report["failed"]]
            progress_callback(
                f"⚠️ Best story after {MAX_RETRIES + 1} attempts still has issues: {', '.join(failed_names)}",
                "error"
            )
        strength = best_story.get("story_strength", 0) if best_story else 0
        name = (best_story.get("character") or {}).get("name", "Unknown") if best_story else "Unknown"
        location = (best_story.get("location") or {}).get("name", "Unknown") if best_story else "Unknown"
        progress_callback(f"✅ Story generated: {name} in {location} (Strength: {strength}/100)", "success")
    
    return best_story, best_report


def generate_story_variants(title, duration_minutes=20, episode_type="build", progress_callback=None):
    """
    Generate 2 story variants with different temperatures, pick the best.
    
    Returns:
        Tuple of (best_story, quality_report, all_variants)
    """
    if progress_callback:
        progress_callback("🎲 A/B Mode: Generating 2 story variants...", "info")
    
    story_dna = load_story_dna()
    config = load_config()
    div_context = diversity_tracker.get_diversity_context()
    
    prompt = _build_story_prompt(story_dna, title, duration_minutes, episode_type, div_context)
    
    temperatures = [0.7, 0.85]
    variants = []
    
    for i, temp in enumerate(temperatures):
        if progress_callback:
            progress_callback(f"🧠 Variant {i+1}/{len(temperatures)} (temperature={temp})...", "batch")
        
        try:
            story = generate_json(prompt, temperature=temp, max_tokens=8000)
            story["duration_minutes"] = duration_minutes
            story["episode_type"] = episode_type
            story["_variant_temperature"] = temp
            
            report = validate_story(story)
            strength = story.get("story_strength", 0)
            
            variants.append({
                "story": story,
                "report": report,
                "strength": strength,
                "temperature": temp,
                "quality_score": report["passed_count"] * 10 + strength
            })
            
            if progress_callback:
                name = story.get("character", {}).get("name", "Unknown")
                progress_callback(
                    f"✓ Variant {i+1}: {name} | Strength: {strength} | Quality: {report['passed_count']}/{report['total_checks']}",
                    "success"
                )
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Variant {i+1} failed: {e}", "error")
    
    if not variants:
        raise Exception("All variants failed to generate")
    
    # Pick best variant
    variants.sort(key=lambda v: v["quality_score"], reverse=True)
    best = variants[0]
    
    if progress_callback:
        progress_callback(
            f"🏆 Best variant: temperature={best['temperature']} | "
            f"Strength: {best['strength']} | Quality: {best['report']['passed_count']}/{best['report']['total_checks']}",
            "success"
        )
    
    # Return best story + report, and store variants data in story for saving
    best["story"]["_variants_summary"] = [
        {"temperature": v["temperature"], "strength": v["strength"], "quality_score": v["quality_score"],
         "character_name": v["story"].get("character", {}).get("name", "?")} 
        for v in variants
    ]
    
    return best["story"], best["report"]


# =============================================================================
# STEP 3: ELEMENTS — Analyze & Generate Character/Object References
# =============================================================================

def analyze_elements(story, narration, progress_callback=None):
    """
    Analyze story + narration to identify ALL recurring Elements needed for video generation.
    
    Elements are ONLY characters and specific measurable objects that need reference images
    for consistent visual identity across Kling 3 Pro video generation.
    
    Each element gets one reference image (2:3 PORTRAIT) generated via Nanobanana Pro.
    ALL elements get CLEAN WHITE STUDIO BACKGROUND for Kling import.
    
    Args:
        story: Complete story dict
        narration: Complete narration dict
        progress_callback: Optional callback(message, type)
    
    Returns:
        List of element dicts with id, label, description, and frontal_prompt
    """
    if progress_callback:
        progress_callback("🔍 Analyzing narration for ALL recurring visual elements...", "info")
    
    char = story.get("character", {})
    companion = char.get("companion", {})
    loc = story.get("location", {})
    construction = story.get("construction", {})
    
    # Build FULL narration text for thorough analysis
    full_narration_parts = []
    if narration.get("intro", {}).get("narration_text"):
        full_narration_parts.append(f"INTRO: {narration['intro']['narration_text']}")
    for p in narration.get('phases', []):
        name = p.get('phase_name', '')
        text = p.get('narration_text', '')
        full_narration_parts.append(f"PHASE [{name}]: {text}")
    if narration.get("outro", {}).get("narration_text"):
        full_narration_parts.append(f"OUTRO: {narration['outro']['narration_text']}")
    
    full_narration_text = "\n\n".join(full_narration_parts)
    
    prompt = f"""You are a video production supervisor. Read this narration script carefully and 
identify EVERY visual element that appears MORE THAN ONCE across different scenes.

The goal is to create reference images so that Kling 3 video generation produces consistent visuals.
If an object, vehicle, tool, or location appears in 2 or more scenes, it MUST be listed as an element.

STORY CHARACTER:
- Name: {char.get('name', 'Unknown')}
- Age: {char.get('age', 'Unknown')}
- Physical: {char.get('physical_description', 'Unknown')}
- Companion: {companion.get('name', 'None')} ({companion.get('breed', 'None')})

LOCATION: {loc.get('name', 'Unknown')} — {loc.get('terrain', 'wilderness')}

CONSTRUCTION: {construction.get('type', 'shelter')} — {construction.get('materials', 'Unknown')}

FULL NARRATION SCRIPT:
{full_narration_text}

═══ EXTRACTION RULES ═══

Read the narration above WORD BY WORD. Extract elements in these categories ONLY:

1. CHARACTERS — protagonist + companion (if any). Extreme physical detail:
   age, height, build, skin tone, hair color/style, facial hair, eye color, 
   clothing (specific brands/types), footwear, accessories (glasses, hat, watch).

2. VEHICLES & TRANSPORT — ANY vehicle mentioned: truck, car, ATV, snowmobile, canoe, 
   horse, etc. Include make/model/color if mentioned or implied. If the character 
   "drives" or "arrives" somewhere, there's a vehicle!

3. SPECIFIC MEASURABLE OBJECTS — objects that must look identical across scenes:
   tents, stoves, boats, generators, trailers, backpacks, specific tools that are
   visually prominent (a distinctive axe, a custom knife). Do NOT include generic
   hand tools or small items.

⚠️ DO NOT INCLUDE ENVIRONMENTS OR LOCATIONS — these are handled separately by the
   Visual Storyboard Chain system.

═══ JSON FORMAT ═══

For each element, provide:
- id: snake_case identifier
- label: Display name
- category: "character" | "vehicle" | "object"
- description: Extremely detailed visual description
- appears_in: List of phase names where this element appears (be thorough!)
- frontal_prompt: Image generation prompt (see rules below)

FRONTAL PROMPT RULES (ALL elements get PORTRAIT 3:4 format with STUDIO BACKGROUND):
- For CHARACTERS: "Close-up chest-up portrait on a CLEAN WHITE STUDIO BACKGROUND. [extremely detailed face and upper body description]. 
  Facing camera directly, shoulders and head visible, eye-level angle. Sharp focus on face. Studio lighting, no shadows, no environment."
  IMPORTANT: Character portraits must show FACE AND UPPER BODY ONLY — NO full body shots. Think passport photo style but more cinematic.
- For COMPANION ANIMALS: "Close-up portrait on a CLEAN WHITE STUDIO BACKGROUND. [detailed breed, fur, size description].
  Facing camera, head and shoulders visible. Studio lighting, no shadows, no environment."
- For VEHICLES: "Studio portrait of [vehicle] on CLEAN WHITE BACKGROUND. [detailed description].
  Three-quarter front angle, entire vehicle visible, studio lighting, no environment."
- For OBJECTS: "Studio portrait of [object] on CLEAN WHITE BACKGROUND. [detailed description].
  Centered, entire object visible, studio lighting, no environment."
- NEVER use character names — use descriptive terms ("a rugged man", "a large dog")
- NEVER place elements in any scene or environment — PURE WHITE STUDIO BACKGROUND ONLY
- Prompts must be self-contained and photorealistic

Return JSON:
{{
    "elements": [
        {{
            "id": "protagonist",
            "label": "Jack Harlan",
            "category": "character",
            "description": "Rugged man in his mid-40s, 6'1, muscular build...",
            "appears_in": ["Arrival", "Base Camp", "Building Phase 1"],
            "frontal_prompt": "Close-up chest-up portrait on a clean white studio background. A rugged, weathered man in his mid-40s, facing the camera directly. Tanned, wind-burned skin. Short-cropped brown hair with grey at the temples. Thick brown beard with grey streaks. Intense blue eyes, crow's feet. He wears a faded olive Carhartt jacket over a red flannel shirt. Shoulders and head visible, eye-level angle. Sharp focus on face. Studio lighting, no shadows, clean white background."
        }},
        {{
            "id": "pickup_truck",  
            "label": "Ford F-250 Pickup",
            "category": "vehicle",
            "description": "A beat-up dark blue Ford F-250 with mud-caked fenders...",
            "appears_in": ["Arrival", "Supply Run", "Final Push"],
            "frontal_prompt": "Cinematic 16:9 shot of a beat-up dark blue Ford F-250 pickup truck parked on a dirt road in a dense forest. The truck has mud-caked wheel wells, a dented tailgate, and a bed loaded with lumber and tools. Forest backdrop, overcast sky. Shot on RED V-Raptor, shallow depth of field."
        }}
    ]
}}

CRITICAL RULES:
- Protagonist is ALWAYS Element 1
- Companion (if any) is ALWAYS Element 2  
- Maximum 12 elements (be exhaustive but skip truly one-time items)
- If an item appears in 2+ scenes, it MUST be included
- Pay special attention to vehicles — they are almost always missed!
- Characters ALWAYS get WHITE BACKGROUND prompts
- All other elements get cinematic 16:9 in their natural setting

Return ONLY the JSON object."""

    result = generate_json(prompt, temperature=0.3, max_tokens=6000)
    elements = result.get("elements", [])
    
    if progress_callback:
        progress_callback(
            f"✅ Found {len(elements)} elements: {', '.join(e.get('label', '?') for e in elements)}",
            "success"
        )
    
    return elements


def generate_elements(elements_list, project_dir, progress_callback=None):
    """
    Generate one 2:3 PORTRAIT reference image per Element using Nanobanana Pro.
    
    No reference images are used — each image is generated independently.
    Images are saved as {element_id}.png in elements/ directory.
    
    Args:
        elements_list: List of element dicts from analyze_elements()
        project_dir: Path to project directory
        progress_callback: Optional callback
    
    Returns:
        Updated elements list with image_filename field
    """
    elements_dir = os.path.join(project_dir, "elements")
    
    # Clean old elements
    if os.path.exists(elements_dir):
        import shutil
        shutil.rmtree(elements_dir)
    os.makedirs(elements_dir, exist_ok=True)
    
    generated = []
    
    for i, element in enumerate(elements_list):
        elem_id = element.get("id", f"element_{i+1}")
        label = element.get("label", f"Element {i+1}")
        
        if progress_callback:
            progress_callback(
                f"🎨 Generating Element {i+1}/{len(elements_list)}: {label}...",
                "batch"
            )
        
        filename = f"{elem_id}.png"
        image_path = os.path.join(elements_dir, filename)
        frontal_prompt = element.get("frontal_prompt", element.get("description", ""))
        
        try:
            # Force 16:9 aspect ratio — override config
            _generate_element_image(frontal_prompt, image_path)
            if progress_callback:
                progress_callback(f"  ✓ {filename}", "success")
        except Exception as e:
            if progress_callback:
                progress_callback(f"  ❌ {label} failed: {str(e)[:100]}", "error")
            filename = None  # Mark as failed but still save element data
        
        generated.append({
            "element_id": elem_id,
            "label": label,
            "category": element.get("category", "unknown"),
            "description": element.get("description", ""),
            "appears_in": element.get("appears_in", []),
            "frontal_prompt": frontal_prompt,
            "image_filename": filename
        })
    
    if progress_callback:
        success_count = sum(1 for e in generated if e.get("image_filename"))
        progress_callback(
            f"✅ Generated {success_count}/{len(elements_list)} element images",
            "success"
        )
    
    return generated


def _generate_element_image(prompt, output_path):
    """
    Generate a single element reference image in 3:4 PORTRAIT format for Kling.
    Uses Nanobanana Pro without any reference images.
    """
    client = init_client()
    
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["Image"],
            image_config=types.ImageConfig(
                aspect_ratio="3:4",
            ),
        ),
    )
    
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                image = part.as_image()
                image.save(output_path)
                return output_path
    
    raise Exception("No image generated — response contained no image parts")


def regenerate_single_element(element, project_dir, progress_callback=None):
    """
    Regenerate the reference image for a single element.
    
    Args:
        element: Element dict (must have element_id and frontal_prompt)
        project_dir: Path to project directory
        progress_callback: Optional callback
    
    Returns:
        Updated element dict with new image_filename
    """
    elements_dir = os.path.join(project_dir, "elements")
    os.makedirs(elements_dir, exist_ok=True)
    
    elem_id = element.get("element_id", "unknown")
    label = element.get("label", elem_id)
    filename = f"{elem_id}.png"
    image_path = os.path.join(elements_dir, filename)
    prompt = element.get("frontal_prompt", element.get("description", ""))
    
    if progress_callback:
        progress_callback(f"🎨 Regenerating {label}...", "info")
    
    _generate_element_image(prompt, image_path)
    element["image_filename"] = filename
    
    if progress_callback:
        progress_callback(f"✅ {label} regenerated", "success")
    
    return element


def edit_element_with_ai(element, feedback, project_dir, progress_callback=None):
    """
    Modify an element's frontal_prompt using AI based on user feedback,
    then regenerate the image.
    
    Args:
        element: Element dict
        feedback: User instructions for what to change
        project_dir: Path to project directory
        progress_callback: Optional callback
        
    Returns:
        Updated element dict
    """
    old_prompt = element.get("frontal_prompt", element.get("description", ""))
    label = element.get("label", element.get("element_id", "unknown"))
    
    if progress_callback:
        progress_callback(f"🧠 Refining prompt for {label}...", "info")
        
    system_prompt = f"""You are an expert AI image prompt engineer.
The user wants to modify an existing image generation prompt for a visual element.

CURRENT PROMPT:
{old_prompt}

USER FEEDBACK / INSTRUCTIONS:
{feedback}

CRITICAL RULES FOR THE NEW PROMPT:
1. Incorporate the user's feedback naturally into the prompt.
2. YOU MUST KEEP THE FOLLOWING PORTRAIT CONSTRAINT EXACTLY AS DESCRIBED:
   - For Characters/Animals: "Close-up chest-up portrait on a CLEAN WHITE STUDIO BACKGROUND... Facing camera directly, shoulders and head visible, eye-level angle. Sharp focus on face. Studio lighting, no shadows, no environment."
   - For Vehicles/Objects: "Studio portrait on CLEAN WHITE BACKGROUND... Studio lighting, no environment."
3. NEVER place the element in a scene (e.g., no forests, no cabins, no snow). Pure white background ONLY.
4. Keep the high level of cinematic detail for the subject itself.

Return ONLY the new, complete image generation prompt as plain text. No markdown, no explanations."""

    try:
        # We can just use the standard generate_content for a text response
        client = init_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL_FLASH,
            contents=[system_prompt]
        )
        new_prompt = response.text.strip()
        
        if progress_callback:
            progress_callback(f"🎨 Generating new image for {label}...", "batch")
            
        element["frontal_prompt"] = new_prompt
        
        # Save old prompt for history just in case
        if "_prompt_history" not in element:
            element["_prompt_history"] = []
        element["_prompt_history"].append(old_prompt)
        
        # Now regenerate using the new prompt
        return regenerate_single_element(element, project_dir, progress_callback)
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Edit failed for {label}: {e}", "error")
        raise Exception(f"Failed to edit element: {e}")



# =============================================================================
# SYSTEM 1: CINEMATIC ANALYZER (Chapter → Storyboard)
# =============================================================================


def cinematic_analyze_chapter(story, chapter_narration, chapter_index, elements, progress_callback=None):
    """
    Analyze a chapter's narration and produce a complete storyboard with bridge scenes.
    
    Implements:
    - Deep process understanding (real-world construction sequence)
    - Action decomposition into atomic visible actions
    - Gap analysis and bridge scene insertion
    - Tool validation per action
    - Construction sequence logic (reorder if narration is out of real-world order)
    - Temporal logic (realistic progress per scene group)
    
    Args:
        story: Complete story dict
        chapter_narration: The narration text for this chapter
        chapter_index: Which chapter (0-based)
        elements: List of element dicts
        progress_callback: Optional callback
    
    Returns:
        Dict with 'storyboard' (list of scene rows) and metadata
    """
    if progress_callback:
        progress_callback(f"🧠 Analyzing Chapter {chapter_index + 1} cinematically...", "info")
    
    char = story.get("character", {})
    companion = char.get("companion", {})
    loc = story.get("location", {})
    construction = story.get("construction", {})
    timeline = story.get("timeline", {})
    
    # Build element reference for the prompt
    element_refs = []
    for elem in elements:
        element_refs.append(f"@{elem.get('label', elem.get('element_id', '?'))} — {elem.get('description', '')[:80]}")
    element_context = "\n".join(element_refs)
    
    prompt = f"""You are a CINEMATIC STORYBOARD ANALYST for a survival documentary.
Your job is to transform literary narration into a COMPLETE visual sequence — as if you
were planning every single shot for a real film crew.

CHAPTER NARRATION:
\"\"\"{chapter_narration}\"\"\"

STORY CONTEXT:
- Character: {char.get('name', 'Unknown')} — {char.get('description', '')}
- Companion: {companion.get('type', 'none')} — {companion.get('description', '')}
- Location: {loc.get('name', 'Unknown')} — {loc.get('terrain', 'wilderness')}
- Construction: {construction.get('type', 'cabin')}
- Timeline: {timeline.get('total_days', 42)} days total
- Chapter: {chapter_index + 1}

AVAILABLE ELEMENTS:
{element_context}

═══════════════════════════════════════════════════
STEP 1: DEEP PROCESS UNDERSTANDING (do this mentally FIRST)
═══════════════════════════════════════════════════

Before writing ANY scene, ask yourself:
- What REAL physical process does this chapter describe?
- What are the ACTUAL steps a real person would perform? Not the literary shortcut.
- What tools, materials, and movements are involved at EACH micro-step?
- Where is the character standing at each moment? What's in their hands?

Example: "drives the axe into frozen wood, clearing spruce saplings" = CLEARING LOW BRUSH.
The axe hits small saplings at ground level. NOT felling large trees. This distinction
is critical for accurate video.

═══════════════════════════════════════════════════
STEP 2: SCENE STATE THINKING (track between EVERY scene)
═══════════════════════════════════════════════════

Between each scene, mentally track these states:
- WHERE is the character? (in the truck, stepping out, at the clearing, etc.)
- WHAT is in their hands? (nothing, steering wheel, axe, mallet, etc.)
- WHAT did they just finish? (driving, chopping, resting, etc.)
- WHAT do they need to DO before the next narrated action can begin?

If the state doesn't match (e.g., character is at the truck but next narrated action
is chopping in the clearing), you MUST insert bridge scenes to connect them:
  truck → exit truck → look around → grab tool → walk to clearing → arrive → position → chop

═══════════════════════════════════════════════════
STEP 3: MANDATORY BRIDGE TYPES (never skip these)
═══════════════════════════════════════════════════

You MUST insert bridges for ALL of these transitions:

🚗 EXIT VEHICLE: Character is in/at vehicle → needs to get out
   → 1 bridge: exits vehicle, looks at surroundings

🚶 CHANGE LOCATION: Character moves from Location A to Location B
   → 1-2 bridges: walks/trudges through terrain, arrives at new location

🔧 CHANGE TOOL: Character switches from one tool to another
   → 1 bridge: puts down old tool, picks up / retrieves new tool

🏗️ START NEW ACTIVITY: Character begins a completely different task
   → 1-2 bridges: prepares position, grabs equipment, evaluates the task

⏰ TIME JUMP: Narration implies hours/days have passed
   → 1 bridge showing result + suggest "Day X" card

👁️ EVALUATE/SURVEY: Character looks at what they've done or what's ahead
   → These are POWERFUL bridges — a character pausing to LOOK at their work
     gives the viewer time to absorb the progress

═══════════════════════════════════════════════════
REFERENCE EXAMPLE — CORRECT bridge density
═══════════════════════════════════════════════════

Here is how Chapter 1 SHOULD look (from our production manual).
Notice: EVERY logical gap between narrated actions gets a bridge:

# | Type     | Action                                  | Gap filled
--|----------|-----------------------------------------|------------------
1 | NARRATED | Erik parks the pickup, kills engine      | (start)
2 | BRIDGE   | Erik exits truck, looks at vast terrain  | exit vehicle
3 | NARRATED | Gus leaps from truck bed into snow       |
4 | BRIDGE   | Erik grabs felling axe from truck bed    | retrieve tool
5 | BRIDGE   | Erik and Gus walk toward the forest edge | change location
6 | BRIDGE   | Erik arrives at clearing, evaluates land | start new activity
7 | BRIDGE   | Erik grips axe with both hands, positions| prepare for action
8 | NARRATED | Erik drives axe into frozen wood...      | (now makes sense!)

That's 5 bridges for just 3 narrated scenes. This is the CORRECT density.
The viewer sees every physical step — nothing is skipped.

═══════════════════════════════════════════════════
BRIDGE DENSITY TABLE
═══════════════════════════════════════════════════

| Gap type                              | Bridges needed |
|---------------------------------------|---------------|
| Minor (same location, small time skip)| 0-1           |
| Medium (location OR tool change)      | 1-2           |
| Major (different activity entirely)   | 2-3           |
| Time jump (days pass)                 | 1 + Day card  |

═══════════════════════════════════════════════════
TOOL VALIDATION (every action must use the RIGHT tool)
═══════════════════════════════════════════════════

- Chopping brush/wood → AXE
- Hammering stakes into ground → MALLET or HAMMER (NOT axe)
- Cutting twine/rope → KNIFE
- Measuring → TAPE MEASURE or marked stick
- Digging → SHOVEL or PICKAXE
- Notching logs → AXE + CHISEL
- Lifting/moving heavy logs → PEAVEY or bare hands + leverage

═══════════════════════════════════════════════════
CONSTRUCTION SEQUENCE (reorder if narration is wrong)
═══════════════════════════════════════════════════

1. Clear the land FIRST
2. THEN mark footprint with stakes
3. THEN dig foundation
4. THEN lay first logs
5. THEN stack walls
6. THEN roof structure
7. THEN chimney/stove
8. THEN insulation/chinking
9. THEN door/windows

If narration puts staking before clearing is done, adjust the sequence and add
a Day card to justify the time needed for clearing to be complete.

═══════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════

Return a JSON object:
{{
    "process_understanding": "1-2 sentence summary of what physical process this chapter covers",
    "locations_needed": ["truck_area", "clearing", "forest_edge"],
    "storyboard": [
        {{
            "scene_num": 1,
            "type": "narrated",
            "narration_excerpt": "The exact narration text for this scene (or null for bridges)",
            "action": "Detailed description of what physically happens on screen",
            "location_id": "clearing",
            "elements": ["@Erik Lindqvist"],
            "time_of_day": "morning",
            "weather": "overcast, cold",
            "tools": ["axe"],
            "duration": "10s",
            "progress_delta": "+5% ground cleared",
            "bridge_reason": null,
            "notes": "Optional notes"
        }},
        {{
            "scene_num": 2,
            "type": "bridge",
            "narration_excerpt": null,
            "action": "Erik wipes sweat from his brow, surveys the remaining dense brush ahead",
            "location_id": "clearing",
            "elements": ["@Erik Lindqvist"],
            "time_of_day": "morning",
            "weather": "overcast, cold",
            "tools": [],
            "duration": "5s",
            "progress_delta": null,
            "bridge_reason": "Character evaluates progress before next action",
            "notes": null
        }}
    ],
    "total_narrated": 8,
    "total_bridges": 7,
    "total_scenes": 15,
    "estimated_video_duration_seconds": 225,
    "day_card_suggestions": ["Insert 'Day 2' card between scene X and Y"]
}}

═══════════════════════════════════════════════════
FINAL RULES
═══════════════════════════════════════════════════

- DURATION per scene (choose based on complexity):
  • 5s — Simple bridges: walking, turning, looking around, transitions
  • 8s — Standard bridges with some action: picking up a tool, opening a door, stepping out of a vehicle
  • 10s — Narrated scenes with moderate action: surveying an area, reacting emotionally, examining something
  • 12-15s — Narrated scenes with complex processes: building, chopping, assembling, detailed craftsmanship
  Assign the "duration" field to each scene (e.g. "5s", "8s", "10s", "12s", "15s")
- Narrated scenes: narration plays as voiceover
- Bridge scenes: AMBIENT SOUND ONLY (wind, footsteps, tools), NO narration
- Use FULL element names as they appear in AVAILABLE ELEMENTS (e.g. "@Erik Lindqvist" not "@Erik")
- Be GENEROUS with bridges — they make the video feel real and cinematic
- NEVER skip the setup for an action (grabbing tools, walking, positioning)
- LANGUAGE RULES: 
  1. Write the `action`, `visual_description`, and `sfx` fields IN SPANISH (e.g. "Erik sale de la camioneta"). 
  2. Keep ALL element names (@Erik Lindqvist) in English.
  3. CRITICAL: The `narration` field MUST BE the EXACT text in ENGLISH from the original script. DO NOT translate the narration to Spanish.

⚠️ CRITICAL: NO MONTAGES — DECOMPOSE EVERY PROCESS ⚠️

NEVER write "montage of...", "series of shots showing...", or "sequence of quick cuts".
Each physical step MUST be its own scene. The audience needs to SEE every action in detail.

If the narration describes a process (building, setting up, organizing, chopping), decompose it like this:

BAD (compressed): "Montaje: Erik monta la tienda de campaña rápidamente" (1 scene)
GOOD (decomposed):
  Scene N [bridge]: Erik desdobla la lona de la tienda sobre el suelo helado
  Scene N+1 [narrated]: Erik clava las estacas de la tienda en la tierra congelada con un mazo
  Scene N+2 [bridge]: Erik extiende las varillas metálicas y las encaja en los ojales
  Scene N+3 [narrated]: La tienda queda tensa, Erik ajusta las cuerdas de amarre a un árbol cercano

Each step = 1 scene = 1 continuous camera shot of 15 seconds.
Ask yourself: "Could a real camera film this in ONE 15-second take?" If not, SPLIT IT.

═══════════════════════════════════════════════════
SELF-CHECK (do this AFTER generating the storyboard)
═══════════════════════════════════════════════════

Count your bridges. If bridges < 30% of total scenes, you are being too conservative.
Go back and look for skipped transitions:
- Did the character teleport between locations?
- Did a tool appear in their hands without being picked up?
- Did a new activity start without preparation?
- Did time pass without showing the result?

Also check for COMPRESSED ACTIONS:
- Does any scene use words like "montaje", "secuencia", "serie de planos", "muestra rápidamente"?
  → If YES: that scene is compressing multiple actions. SPLIT IT into separate scenes.
- Does any scene describe more than ONE distinct physical action?
  → If YES: each action needs its own scene.
- Could each scene be filmed in a single 15-second continuous camera shot?
  → If NO: split it until it can.

Add the missing scenes until every process is fully decomposed.
"""

    try:
        if progress_callback:
            progress_callback("  ⏳ Running deep cinematic analysis...", "batch")
        
        result = generate_json(prompt, temperature=0.4, max_tokens=15000)
        
        storyboard = result.get("storyboard", [])
        
        # Normalize scene_number to scene_num for internal engine processing
        for scene in storyboard:
            if "scene_number" in scene and "scene_num" not in scene:
                scene["scene_num"] = scene.pop("scene_number")
        
        if progress_callback:
            narrated = sum(1 for s in storyboard if s.get("type") == "narrated")
            bridges = sum(1 for s in storyboard if s.get("type") == "bridge")
            progress_callback(
                f"✅ Storyboard: {len(storyboard)} scenes ({narrated} narrated + {bridges} bridges)",
                "success"
            )
            if result.get("day_card_suggestions"):
                for suggestion in result["day_card_suggestions"]:
                    progress_callback(f"  📋 {suggestion}", "info")
        
        return result
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Cinematic analysis failed: {str(e)[:150]}", "error")
        return {"error": str(e), "storyboard": []}


# =============================================================================
# SYSTEM 2: SCENE STATE TRACKER (Sequential State Evolution)
# =============================================================================


def init_scene_state(story, chapter_index, first_location_id="clearing"):
    """
    Create the initial JSON state for the start of a chapter.
    
    Args:
        story: Complete story dict
        chapter_index: Which chapter (0-based)
        first_location_id: The starting location
    
    Returns:
        Initial state dict
    """
    char = story.get("character", {})
    companion = char.get("companion", {})
    
    return {
        "scene": 0,
        "chapter": chapter_index + 1,
        "environment": {
            "ground_cleared_pct": 0,
            "ground_description": "untouched dense brush and saplings",
            "structures_built": [],
            "objects_on_ground": []
        },
        "tools": {
            "available": ["axe", "canvas_bag"],
            "in_use": None,
            "visible": {}
        },
        "characters": {
            char.get("name", "protagonist").lower(): {
                "state": "fresh, determined",
                "location": first_location_id
            }
        },
        "time_of_day": "morning",
        "weather": "overcast, cold",
        "location_id": first_location_id,
        "location_image": None,
        "location_changed": True  # First scene always needs an image
    }


def evolve_scene_state(previous_state, scene_row, progress_callback=None):
    """
    Evolve the scene state based on what happens in this scene.
    
    Uses LLM to intelligently update the state based on the scene action,
    ensuring realistic progress and consistency.
    
    Args:
        previous_state: The JSON state from the previous scene
        scene_row: The storyboard row for this scene
        progress_callback: Optional callback
    
    Returns:
        Updated state dict
    """
    prompt = f"""You are a scene state tracker for a survival documentary.

PREVIOUS STATE:
{json.dumps(previous_state, indent=2)}

CURRENT SCENE ACTION:
- Scene {scene_row.get('scene_num')}: {scene_row.get('action', 'unknown')}
- Type: {scene_row.get('type', 'narrated')}
- Tools used: {json.dumps(scene_row.get('tools', []))}
- Progress delta: {scene_row.get('progress_delta', 'none')}
- Time of day: {scene_row.get('time_of_day', 'same')}
- Weather: {scene_row.get('weather', 'same')}
- Location: {scene_row.get('location_id', 'same')}

UPDATE RULES:
1. Progress increments must be REALISTIC: ground_cleared_pct goes up ~3-5% per chopping scene
2. After a "Day X" card, progress can jump significantly (15% → 60%)
3. Tools: if character picks up a tool, update "in_use". If puts down, update "visible"
4. If location changes, set location_changed: true
5. If environment changes significantly (more cleared, objects added, lighting changes), set location_changed: true
6. If NOTHING visually changed in the environment, set location_changed: false
7. Character state should reflect physical work (sweaty, tired, etc.)

Return the UPDATED state as JSON:
{{
    "scene": {scene_row.get('scene_num', 0)},
    "chapter": {previous_state.get('chapter', 1)},
    "environment": {{
        "ground_cleared_pct": <number>,
        "ground_description": "<what the ground looks like now>",
        "structures_built": [<list of permanent additions>],
        "objects_on_ground": [<visible objects like tools, materials>]
    }},
    "tools": {{
        "available": [<all tools available>],
        "in_use": "<tool currently being used or null>",
        "visible": {{"<tool>": "<where it is>"}}
    }},
    "characters": {{
        "<name>": {{ "state": "<physical/emotional state>", "location": "<where>" }}
    }},
    "time_of_day": "<current>",
    "weather": "<current>",
    "location_id": "<current location>",
    "location_image": "<suggested filename like loc_NNN.png>",
    "location_changed": <true if new image needed, false if reuse previous>
}}"""

    try:
        result = generate_json(prompt, temperature=0.2, max_tokens=2000, model=GEMINI_MODEL_FLASH)
        return result
    except Exception as e:
        if progress_callback:
            progress_callback(f"⚠️ State evolution failed for scene {scene_row.get('scene_num')}: {e}", "error")
        # Fallback: return previous state with updated scene number
        fallback = dict(previous_state)
        fallback["scene"] = scene_row.get("scene_num", previous_state["scene"] + 1)
        return fallback


def evaluate_location_diff(current_state, previous_state):
    """
    Compare two scene states and determine if a new location image is needed.
    
    Returns:
        Dict with 'needs_new_image' (bool) and 'triggers' (list of reasons)
    """
    triggers = []
    
    # Check if the state tracker already flagged it
    if current_state.get("location_changed", False):
        triggers.append("state_tracker_flagged")
    
    # Check location change
    if current_state.get("location_id") != previous_state.get("location_id"):
        triggers.append(f"location_changed: {previous_state.get('location_id')} → {current_state.get('location_id')}")
    
    # Check construction progress
    curr_pct = current_state.get("environment", {}).get("ground_cleared_pct", 0)
    prev_pct = previous_state.get("environment", {}).get("ground_cleared_pct", 0)
    if curr_pct - prev_pct >= 10:
        triggers.append(f"construction_progress: {prev_pct}% → {curr_pct}%")
    
    # Check new structures
    curr_structs = set(current_state.get("environment", {}).get("structures_built", []))
    prev_structs = set(previous_state.get("environment", {}).get("structures_built", []))
    new_structs = curr_structs - prev_structs
    if new_structs:
        triggers.append(f"new_structures: {new_structs}")
    
    # Check new objects on ground
    curr_objs = set(current_state.get("environment", {}).get("objects_on_ground", []))
    prev_objs = set(previous_state.get("environment", {}).get("objects_on_ground", []))
    new_objs = curr_objs - prev_objs
    if new_objs:
        triggers.append(f"new_objects: {new_objs}")
    
    # Check time of day change
    if current_state.get("time_of_day") != previous_state.get("time_of_day"):
        triggers.append(f"time_change: {previous_state.get('time_of_day')} → {current_state.get('time_of_day')}")
    
    # Check weather change
    if current_state.get("weather") != previous_state.get("weather"):
        triggers.append(f"weather_change: {previous_state.get('weather')} → {current_state.get('weather')}")
    
    return {
        "needs_new_image": len(triggers) > 0,
        "triggers": triggers
    }


def generate_location_image_prompt(current_state, previous_state, diff_result):
    """
    Generate the text prompt for creating a new location image.
    
    If there's a previous image, the prompt references it for visual consistency.
    If standalone (new location or dream), generates from scratch.
    
    Args:
        current_state: Current scene state
        previous_state: Previous scene state (can be None for first scene)
        diff_result: Output from evaluate_location_diff()
    
    Returns:
        Dict with 'prompt' (text), 'use_reference' (bool), 'reference_image' (filename or None)
    """
    location_id = current_state.get("location_id", "unknown")
    env = current_state.get("environment", {})
    time_of_day = current_state.get("time_of_day", "morning")
    weather = current_state.get("weather", "overcast")
    scene_num = current_state.get("scene", 0)
    
    # Build environment description from state
    env_details = []
    if env.get("ground_cleared_pct", 0) > 0:
        env_details.append(f"{env['ground_cleared_pct']}% of ground cleared, exposed frozen earth")
    if env.get("structures_built"):
        env_details.append(f"Structures visible: {', '.join(env['structures_built'])}")
    if env.get("objects_on_ground"):
        env_details.append(f"Objects on ground: {', '.join(env['objects_on_ground'])}")
    env_description = ". ".join(env_details) if env_details else env.get("ground_description", "untouched wilderness")
    
    # Determine if reference-based or standalone
    prev_image = previous_state.get("location_image") if previous_state else None
    is_standalone = (
        previous_state is None or 
        current_state.get("location_id") != previous_state.get("location_id") or
        "dream" in location_id.lower() or
        "vision" in location_id.lower()
    )
    
    if is_standalone:
        prompt_text = f"""Real photography, 16:9 landscape format. Ground level eye-height perspective, wide angle lens. {env.get('ground_description', 'Wilderness environment')}. {env_description}. {time_of_day} lighting. {weather} weather. No people. Photorealistic, cinematic, wide shot, 24mm lens. NOT CGI."""
        return {
            "prompt": prompt_text,
            "use_reference": False,
            "reference_image": None,
            "output_filename": f"loc_{scene_num:03d}.png"
        }
    else:
        # Reference-based: describe what changed
        changes = []
        for trigger in diff_result.get("triggers", []):
            if "construction_progress" in trigger:
                changes.append(f"More ground has been cleared — now {env.get('ground_cleared_pct', 0)}% exposed earth")
            elif "new_structures" in trigger:
                changes.append(f"New structures visible: {', '.join(env.get('structures_built', []))}")
            elif "new_objects" in trigger:
                changes.append(f"New objects on the ground: {', '.join(env.get('objects_on_ground', []))}")
            elif "time_change" in trigger:
                changes.append(f"Lighting changed to {time_of_day}")
            elif "weather_change" in trigger:
                changes.append(f"Weather changed to {weather}")
        
        modification = ". ".join(changes) if changes else "Minor environmental changes"
        
        prompt_text = f"""Using the provided reference image as the base environment. Modification: {modification}. Keep everything else identical — same trees, same clearing shape, same snow coverage. Real photography, 16:9 landscape, ground level eye-height. NOT CGI."""
        
        return {
            "prompt": prompt_text,
            "use_reference": True,
            "reference_image": prev_image,
            "output_filename": f"loc_{scene_num:03d}.png"
        }


# =============================================================================
# VALIDATION LAYER: Storyboard Quality Checks
# =============================================================================

# Construction milestones in real-world order
CONSTRUCTION_MILESTONES = [
    "clear", "stake", "dig", "foundation", "lay_logs", "first_logs",
    "notch", "stack_walls", "walls", "frame", "roof", "door", "window", "chimney"
]

# Time of day progression (must go forward within a day)
TIME_ORDER = ["dawn", "early morning", "morning", "late morning", "midday", "noon",
              "early afternoon", "afternoon", "late afternoon", "golden hour",
              "sunset", "dusk", "evening", "night"]


def _normalize_time(t):
    """Normalize a time string to find its position in TIME_ORDER."""
    if not t:
        return -1
    t_lower = t.strip().lower()
    for i, label in enumerate(TIME_ORDER):
        if label in t_lower or t_lower in label:
            return i
    return -1


def _find_milestone(action_text):
    """Find which construction milestone an action corresponds to, if any."""
    if not action_text:
        return None
    action_lower = action_text.lower()
    for milestone in CONSTRUCTION_MILESTONES:
        if milestone in action_lower:
            return milestone
    # Specific keyword mappings
    keyword_map = {
        "chop": "clear", "brush": "clear", "fell": "clear", "tree": "clear",
        "mark": "stake", "measur": "stake", "string": "stake",
        "hammer": "stake", "mallet": "stake",
        "shovel": "dig", "pickaxe": "dig", "trench": "dig",
        "log": "lay_logs", "timber": "lay_logs",
        "wall": "stack_walls", "stack": "stack_walls",
        "roof": "roof", "rafter": "roof",
    }
    for keyword, milestone in keyword_map.items():
        if keyword in action_lower:
            return milestone
    return None


def validate_storyboard(storyboard, original_narration, progress_callback=None):
    """
    Validate a storyboard for completeness, logic, and consistency.
    
    Runs 6 checks:
    1. ORPHAN NARRATION — narration text not covered by any scene
    2. CONSTRUCTION SEQUENCE — steps out of real-world order
    3. MISSING BRIDGES — abrupt changes without transition scenes
    4. PROGRESS MONOTONICITY — cleared % going backward
    5. PHANTOM TOOLS — tools appearing without being available
    6. TIME PROGRESSION — time going backward within a day
    
    Args:
        storyboard: List of scene rows from cinematic_analyze_chapter()
        original_narration: The complete chapter narration text
        progress_callback: Optional callback
    
    Returns:
        Dict with 'valid' (bool), 'errors' (list), 'warnings' (list),
        'score' (0-100), 'summary' (text)
    """
    errors = []   # Must fix before generating prompts
    warnings = [] # Should review but won't block generation
    
    if progress_callback:
        progress_callback("🔍 Validating storyboard...", "info")
    
    # =========================================================================
    # CHECK 1: ORPHAN NARRATION
    # Ensure every sentence of the original narration is covered
    # =========================================================================
    if original_narration:
        # Split narration into sentences
        import re
        sentences = [s.strip() for s in re.split(r'[.!?]+', original_narration) if s.strip() and len(s.strip()) > 10]
        
        # Collect all narration text from scenes (support both field names)
        scene_narrations = " ".join([
            s.get("narration", s.get("narration_excerpt", "")) or "" 
            for s in storyboard 
            if s.get("type") == "narrated" and (s.get("narration") or s.get("narration_excerpt"))
        ]).lower()
        
        orphans = []
        for sentence in sentences:
            # Check if key words from this sentence appear in scene narrations
            words = [w for w in sentence.lower().split() if len(w) > 4]
            if not words:
                continue
            matching_words = sum(1 for w in words if w in scene_narrations)
            coverage = matching_words / len(words) if words else 0
            if coverage < 0.4:  # Less than 40% of key words found
                orphans.append(sentence[:80])
        
        if orphans:
            errors.append({
                "check": "orphan_narration",
                "severity": "error",
                "message": f"{len(orphans)} narration segment(s) not covered by any scene",
                "details": orphans
            })
    
    # =========================================================================
    # CHECK 2: CONSTRUCTION SEQUENCE
    # Steps must follow real-world order
    # =========================================================================
    scene_milestones = []
    for scene in storyboard:
        milestone = _find_milestone(scene.get("action", ""))
        if milestone:
            scene_milestones.append({
                "scene": scene.get("scene_num"),
                "milestone": milestone,
                "action": scene.get("action", "")[:60],
                "order": CONSTRUCTION_MILESTONES.index(milestone) if milestone in CONSTRUCTION_MILESTONES else 999
            })
    
    # Check order
    for i in range(1, len(scene_milestones)):
        curr = scene_milestones[i]
        prev = scene_milestones[i - 1]
        if curr["order"] < prev["order"] - 1:  # Allow going back 1 step (e.g. notch while stacking)
            errors.append({
                "check": "construction_sequence",
                "severity": "error",
                "message": f"Scene {curr['scene']}: '{curr['milestone']}' appears BEFORE '{prev['milestone']}' was completed",
                "details": f"Scene {prev['scene']} ({prev['action']}) → Scene {curr['scene']} ({curr['action']})"
            })
    
    # =========================================================================
    # CHECK 3: MISSING BRIDGES
    # Abrupt changes without transition scenes
    # =========================================================================
    for i in range(1, len(storyboard)):
        curr = storyboard[i]
        prev = storyboard[i - 1]
        
        # Skip if current IS a bridge
        if curr.get("type") == "bridge":
            continue
        
        # Check for abrupt location change
        if (curr.get("location_id") and prev.get("location_id") and 
            curr["location_id"] != prev["location_id"] and 
            prev.get("type") != "bridge"):
            warnings.append({
                "check": "missing_bridge",
                "severity": "warning",
                "message": f"Scene {curr.get('scene_num')}: location changes from '{prev['location_id']}' to '{curr['location_id']}' without a bridge",
                "details": f"Consider adding a walking/transition bridge between scenes {prev.get('scene_num')} and {curr.get('scene_num')}"
            })
        
        # Check for abrupt activity change (different tools)
        curr_tools = set(curr.get("tools", []))
        prev_tools = set(prev.get("tools", []))
        if curr_tools and prev_tools and not curr_tools.intersection(prev_tools) and prev.get("type") != "bridge":
            warnings.append({
                "check": "missing_bridge",
                "severity": "warning",
                "message": f"Scene {curr.get('scene_num')}: tools change from {prev_tools} to {curr_tools} without preparation",
                "details": f"Consider a bridge where character puts down {prev_tools} and picks up {curr_tools}"
            })
    
    # =========================================================================
    # CHECK 4: PROGRESS MONOTONICITY
    # Cleared percentage can only go up (or stay same)
    # =========================================================================
    last_progress = None
    for scene in storyboard:
        delta = scene.get("progress_delta")
        if not delta or delta == "null":
            continue
        # Try to extract a percentage from progress_delta
        import re
        pct_match = re.search(r'(\d+)%', str(delta))
        if pct_match:
            current_pct = int(pct_match.group(1))
            # This is a delta like "+5%", not absolute — but check if negative
            if str(delta).startswith("-"):
                errors.append({
                    "check": "progress_monotonicity",
                    "severity": "error",
                    "message": f"Scene {scene.get('scene_num')}: progress goes BACKWARD ({delta})",
                    "details": "Construction progress can never decrease"
                })
    
    # =========================================================================
    # CHECK 5: PHANTOM TOOLS
    # Tools used in a scene must be plausible
    # =========================================================================
    # Build a set of tools that have been introduced
    known_tools = {"axe", "canvas_bag", "knife", "rope"}  # Default starting tools
    
    for scene in storyboard:
        scene_tools = scene.get("tools", [])
        for tool in scene_tools:
            tool_lower = tool.lower().strip()
            if tool_lower not in known_tools:
                # Check if this tool could have been brought/found
                specialized = {"chainsaw", "power_drill", "crane", "excavator", "bulldozer", "generator"}
                if tool_lower in specialized:
                    errors.append({
                        "check": "phantom_tool",
                        "severity": "error",
                        "message": f"Scene {scene.get('scene_num')}: uses '{tool}' — a power tool in a hand-built survival scenario",
                        "details": "This tool is not plausible in the story context"
                    })
                else:
                    # Add to known tools (character could have it)
                    known_tools.add(tool_lower)
                    warnings.append({
                        "check": "phantom_tool",
                        "severity": "warning",
                        "message": f"Scene {scene.get('scene_num')}: introduces new tool '{tool}' — verify this is available",
                        "details": f"Known tools so far: {known_tools}"
                    })
    
    # =========================================================================
    # CHECK 6: TIME PROGRESSION
    # Time of day must advance forward within a single day
    # =========================================================================
    last_time_idx = -1
    last_time_label = None
    day_boundary_seen = False
    
    for scene in storyboard:
        time = scene.get("time_of_day")
        if not time:
            continue
        
        # Check for day boundary (Day card or significant time skip)
        notes = scene.get("notes", "") or ""
        bridge_reason = scene.get("bridge_reason", "") or ""
        if "day" in notes.lower() or "day" in bridge_reason.lower():
            day_boundary_seen = True
            last_time_idx = -1  # Reset
            continue
        
        time_idx = _normalize_time(time)
        if time_idx == -1:
            continue  # Unknown time format, skip
        
        if last_time_idx > -1 and time_idx < last_time_idx and not day_boundary_seen:
            warnings.append({
                "check": "time_progression",
                "severity": "warning",
                "message": f"Scene {scene.get('scene_num')}: time goes BACKWARD from '{last_time_label}' to '{time}'",
                "details": "Time should only advance. If this is a new day, add a Day card bridge scene."
            })
        
        last_time_idx = time_idx
        last_time_label = time
        day_boundary_seen = False
    
    # =========================================================================
    # CALCULATE SCORE
    # =========================================================================
    total_checks = 6
    error_penalty = len(errors) * 15       # -15 per error
    warning_penalty = len(warnings) * 5    # -5 per warning
    score = max(0, 100 - error_penalty - warning_penalty)
    
    # Summary
    if not errors and not warnings:
        summary = "✅ Storyboard passed all validation checks"
    elif not errors:
        summary = f"⚠️ Storyboard has {len(warnings)} warning(s) — review recommended"
    else:
        summary = f"❌ Storyboard has {len(errors)} error(s) and {len(warnings)} warning(s) — fix before generating prompts"
    
    if progress_callback:
        progress_callback(summary, "info")
        for err in errors:
            progress_callback(f"  ⚠️ {err['message']}", "info")
        for warn in warnings:
            progress_callback(f"  💡 {warn['message']}", "info")
    
    return {
        "valid": len(errors) == 0,
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "summary": summary
    }


# =============================================================================
# STEP 5: SCENE PROMPTS + FRAME A IMAGES
# =============================================================================


def generate_frame_a_images(scenes, project_dir, progress_callback=None):
    """
    Generate Frame A images for all scenes using their frame_a_prompt.
    
    Args:
        scenes: List of scene dicts (must have frame_a_prompt)
        project_dir: Path to project directory
        progress_callback: Optional callback
    
    Returns:
        Updated scenes list with frame_a_filename added to each scene
    """
    frames_dir = os.path.join(project_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    total = len(scenes)
    for i, scene in enumerate(scenes):
        scene_num = scene.get("number", i + 1)
        prompt = scene.get("frame_a_prompt", "")
        if not prompt:
            continue
        
        filename = f"scene_{scene_num}_frame_a.png"
        image_path = os.path.join(frames_dir, filename)
        
        if progress_callback:
            progress_callback(
                f"🖼️ Generating Frame A for scene {scene_num}/{total}...",
                "batch"
            )
        
        try:
            _generate_element_image(prompt, image_path)
            scene["frame_a_filename"] = filename
        except Exception as e:
            if progress_callback:
                progress_callback(
                    f"⚠️ Frame A failed for scene {scene_num}: {str(e)[:100]}",
                    "error"
                )
            scene["frame_a_filename"] = None
    
    if progress_callback:
        generated = sum(1 for s in scenes if s.get("frame_a_filename"))
        progress_callback(
            f"✅ {generated}/{total} Frame A images generated",
            "success"
        )
    
    return scenes


def regenerate_frame_a(scene, project_dir, progress_callback=None):
    """
    Regenerate the Frame A image for a single scene.
    
    Args:
        scene: Scene dict (must have number and frame_a_prompt)
        project_dir: Path to project directory
        progress_callback: Optional callback
    
    Returns:
        Updated scene dict with new frame_a_filename
    """
    frames_dir = os.path.join(project_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    scene_num = scene.get("number", 1)
    prompt = scene.get("frame_a_prompt", "")
    filename = f"scene_{scene_num}_frame_a.png"
    image_path = os.path.join(frames_dir, filename)
    
    if progress_callback:
        progress_callback(f"🖼️ Regenerating Frame A for scene {scene_num}...", "info")
    
    _generate_element_image(prompt, image_path)
    scene["frame_a_filename"] = filename
    
    if progress_callback:
        progress_callback(f"✅ Frame A for scene {scene_num} regenerated", "success")
    
    return scene

def generate_scene_prompts(story, narration, elements, audio_durations=None, progress_callback=None):
    """
    Generate unified Scene Prompts from narration.
    
    Each scene includes:
    - type: "narration" or "narrator_break" or "narrator_intro" or "narrator_outro"
    - narration_text: the text being spoken during this scene
    - duration: seconds (from audio if available, else estimated)
    - frame_a_prompt: image prompt for the starting frame
    - video_prompt: Kling 3 Pro prompt with @Element references
    - elements_used: which elements appear in this scene
    
    Args:
        story: Complete story dict
        narration: Complete narration dict
        elements: List of element dicts from generate_elements()
        audio_durations: Optional dict mapping phase segments to exact durations
        progress_callback: Optional callback
    
    Returns:
        Dict with 'scenes' array and metadata
    """
    if progress_callback:
        progress_callback("🎬 Generating unified Scene Prompts from narration...", "info")
    
    phases = narration.get("phases", [])
    if not phases:
        return {"error": "No narration phases found"}
    
    char = story.get("character", {})
    companion = char.get("companion", {})
    loc = story.get("location", {})
    construction = story.get("construction", {})
    
    # Build element reference map for the prompt
    element_map = []
    for i, elem in enumerate(elements):
        element_map.append(f"@Element{i+1} = {elem.get('label', '?')} ({elem.get('category', '?')}): {elem.get('description', '')[:100]}")
    element_context = "\n".join(element_map)
    
    all_scenes = []
    scene_counter = 0
    
    for phase_idx, phase in enumerate(phases):
        phase_name = phase.get("phase_name", f"Phase {phase_idx + 1}")
        phase_type = phase.get("type", "narration")
        narration_text = phase.get("narration", "")
        
        if not narration_text or narration_text.startswith("[Narration for"):
            continue
        
        # Determine scene type
        is_narrator = phase_type in ("intro", "break", "outro", "presenter_intro", "presenter_break", "close")
        scene_type = f"narrator_{phase_type}" if is_narrator else "narration"
        
        # Estimate duration from text if no audio data
        word_count = len(narration_text.split())
        estimated_duration = max(3, min(15, round(word_count / 2.5)))
        
        # Get audio duration if available
        actual_duration = estimated_duration
        if audio_durations and phase_name in audio_durations:
            actual_duration = audio_durations[phase_name]
        
        # How many scenes for this phase?
        # Short phases (< 15s) = 1 scene, longer phases split into ~8-10s clips
        if actual_duration <= 15:
            num_scenes = 1
        else:
            num_scenes = max(2, round(actual_duration / 10))
        
        if progress_callback:
            progress_callback(
                f"⏳ {phase_name} ({scene_type}): ~{actual_duration}s → {num_scenes} scene(s)...",
                "batch"
            )
        
        # Determine which elements appear in this phase
        phase_elements = []
        for i, elem in enumerate(elements):
            appears_in = elem.get("appears_in", [])
            # Check if element appears in this phase
            if any(phase_name.lower() in a.lower() or a.lower() in phase_name.lower() for a in appears_in):
                phase_elements.append(f"@Element{i+1}")
            elif is_narrator and elem.get("element_id") == "narrator":
                phase_elements.append(f"@Element{i+1}")
        
        # For protagonist, always include in narration scenes
        if not is_narrator and not phase_elements:
            phase_elements = ["@Element1"]
        
        prompt = f"""Generate {num_scenes} scene prompt(s) for this narration segment.

NARRATION TEXT:
\"\"\"{narration_text}\"\"\"

SCENE TYPE: {scene_type}
TOTAL DURATION: ~{actual_duration} seconds across {num_scenes} scene(s)

AVAILABLE ELEMENTS:
{element_context}

ELEMENTS IN THIS PHASE: {', '.join(phase_elements) if phase_elements else 'None specified'}

STORY CONTEXT:
- Character: {char.get('name', 'Unknown')}
- Location: {loc.get('name', 'Unknown')} — {loc.get('terrain', 'wilderness')}
- Construction: {construction.get('type', 'shelter')}

RULES:
1. Split the narration text evenly across {num_scenes} scene(s)
2. frame_a_prompt: Describe the STARTING FRAME image in detail (composition, lighting, camera angle)
3. video_prompt: Use @Element references (NOT character descriptions). Describe MOTION and ACTION only
4. Duration per scene: {max(3, min(15, actual_duration // num_scenes))} seconds
5. For narrator scenes: show the narrator speaking to camera, reference @narrator element if available
6. scene numbers start at {scene_counter + 1}

Return JSON:
{{
    "scenes": [
        {{
            "number": {scene_counter + 1},
            "type": "{scene_type}",
            "phase": "{phase_name}",
            "narration_text": "The exact words spoken during this scene",
            "duration": {max(3, min(15, actual_duration // num_scenes))},
            "frame_a_prompt": "Detailed image prompt for the starting frame...",
            "video_prompt": "@Element1 does action... Camera slowly pans...",
            "elements_used": {json.dumps(phase_elements)}
        }}
    ]
}}"""

        try:
            result = generate_json(prompt, temperature=0.5, max_tokens=8000)
            batch_scenes = result.get("scenes", [])
            
            for s in batch_scenes:
                scene_counter += 1
                s["number"] = scene_counter
                s["type"] = scene_type
                s["phase"] = phase_name
                all_scenes.append(s)
            
            if progress_callback:
                progress_callback(
                    f"✓ {phase_name}: {len(batch_scenes)} scene(s) generated",
                    "success"
                )
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Failed {phase_name}: {str(e)[:150]}", "error")
    
    if progress_callback:
        total_duration = sum(s.get("duration", 8) for s in all_scenes)
        progress_callback(
            f"✅ {len(all_scenes)} scene prompts generated "
            f"(~{total_duration // 60}m {total_duration % 60}s total)",
            "success"
        )
    
    return {
        "total_scenes": len(all_scenes),
        "scenes": all_scenes
    }


# =============================================================================
# SYSTEM 4: SCENE PROMPT WRITER (Video Prompts with All Rules)
# =============================================================================


def generate_video_prompt(scene_row, scene_state, elements, story, is_presenter=False, progress_callback=None):
    """
    Generate a single Kling-ready video prompt for one scene.
    
    Enforces all documented rules from MANUAL_PIPELINE.md:
    - "No music." prefix, "4K." suffix
    - @Element references for characters
    - Camera movements for each cut
    - Simple actions per shot
    - Ambient sound design
    - Sparse dialogue (~1 phrase per 4-5 scenes)
    - @Image1/@Image2 for multi-image transitions
    
    Args:
        scene_row: Storyboard row for this scene
        scene_state: Current state from State Tracker
        elements: List of element dicts
        story: Complete story dict
        is_presenter: True if this is a presenter break scene
        progress_callback: Optional callback
    
    Returns:
        Dict with 'video_prompt', 'metadata', and image references
    """
    char = story.get("character", {})
    loc = story.get("location", {})
    
    # Build element reference map
    element_refs = []
    for elem in elements:
        label = elem.get("label", elem.get("element_id", "?"))
        element_refs.append(f"@{label} = {elem.get('description', '')[:80]}")
    element_context = "\n".join(element_refs)
    
    # Build environment context from state
    env = scene_state.get("environment", {})
    tools = scene_state.get("tools", {})
    characters = scene_state.get("characters", {})
    
    env_description = env.get("ground_description", "wilderness")
    visible_tools = tools.get("visible", {})
    tool_context = ", ".join([f"{t}: {pos}" for t, pos in visible_tools.items()]) if visible_tools else "none visible"
    
    # Scene-specific context
    scene_type = scene_row.get("type", "narrated")
    scene_action = scene_row.get("action", "")
    narration_text = scene_row.get("narration_excerpt", "")
    scene_elements = scene_row.get("elements", [])
    time_of_day = scene_state.get("time_of_day", "morning")
    weather = scene_state.get("weather", "overcast")
    
    if is_presenter:
        prompt = f"""Generate a KLING VIDEO PROMPT for a PRESENTER scene.

SCENE ACTION: {scene_action}
NARRATION (presenter speaks this to camera): "{narration_text}"
ELEMENTS IN SCENE: {json.dumps(scene_elements)}
TIME OF DAY: {time_of_day}
WEATHER: {weather}

AVAILABLE ELEMENTS:
{element_context}

ENVIRONMENT (where the presenter is standing):
- {env_description}
- Visible objects: {tool_context}
- Location image will be attached separately in Kling

RULES:
1. Start with "No music." — ALWAYS
2. Use @ElementName references (e.g. @Jack), not character descriptions
3. Presenter speaks DIRECTLY to camera — medium shot, eye contact
4. 1-2 camera cuts maximum for presenter (medium → close-up is classic)
5. Sound: voice + wind/ambient only. Never add music.
6. End with "4K." — ALWAYS
7. Include a camera movement with each cut (track, push, pull, static)
8. Describe what the presenter DOES while speaking (walks, points, touches)

Return JSON:
{{
    "video_prompt": "No music. [the complete video prompt]. 4K.",
    "scene_type": "presenter",
    "elements_used": {json.dumps(scene_elements)},
    "location_image": "{scene_state.get('location_image', 'unknown')}",
    "duration": 15,
    "narration_excerpt": "{narration_text[:100]}",
    "sound_design": "Description of ambient sounds"
}}"""
    else:
        prompt = f"""Generate a KLING VIDEO PROMPT for a {'NARRATED' if scene_type == 'narrated' else 'BRIDGE (B-roll)'} scene.

SCENE ACTION: {scene_action}
{'NARRATION (voiceover during this scene): "' + narration_text + '"' if narration_text else 'NO NARRATION — ambient sound only (bridge scene)'}
ELEMENTS IN SCENE: {json.dumps(scene_elements)}
TOOLS: {json.dumps(scene_row.get('tools', []))}
TIME OF DAY: {time_of_day}
WEATHER: {weather}

AVAILABLE ELEMENTS:
{element_context}

CURRENT ENVIRONMENT STATE:
- Ground: {env_description}
- Cleared: {env.get('ground_cleared_pct', 0)}%
- Structures: {json.dumps(env.get('structures_built', []))}
- Visible objects: {tool_context}
- Characters: {json.dumps(characters)}
- Location image will be attached separately in Kling

RULES:
1. Start with "No music." — ALWAYS
2. Use @ElementName references (e.g. @Erik, @Gus), not character descriptions
3. Describe MOTION and ACTION — what physically moves and how
4. Camera movements: wide shot, tracking, close-up, aerial — describe each cut's camera
5. Keep each individual shot's action SIMPLE — one movement per shot
6. Use as many camera angle changes as cinematically needed
7. Sound design: ambient only. Wind, cracking wood, footsteps, breathing. NEVER music.
8. End with "4K." — ALWAYS
9. Do NOT mention the reference image in the prompt text (it's attached in Kling)
10. Environment descriptions must match the state tracker data EXACTLY
11. If character uses a tool, the CORRECT tool must be specified (per Tool Validation rules)
12. {'No dialogue in this scene' if not narration_text else 'Sparse dialogue allowed: max 1 short phrase if this scene warrants it (every 4-5 scenes)'}

Return JSON:
{{
    "video_prompt": "No music. [the complete video prompt]. 4K.",
    "scene_type": "{scene_type}",
    "elements_used": {json.dumps(scene_elements)},
    "location_image": "{scene_state.get('location_image', 'unknown')}",
    "duration": 15,
    "narration_excerpt": "{narration_text[:100] if narration_text else 'null'}",
    "sound_design": "Description of ambient sounds",
    "camera_shots": ["Description of each camera angle/movement"]
}}"""

    try:
        result = generate_json(prompt, temperature=0.5, max_tokens=4000, model=GEMINI_MODEL_FLASH)
        return result
    except Exception as e:
        if progress_callback:
            progress_callback(f"⚠️ Prompt generation failed for scene {scene_row.get('scene_num')}: {e}", "error")
        return {
            "video_prompt": f"No music. [FAILED — regenerate this scene]. 4K.",
            "scene_type": scene_type,
            "elements_used": scene_elements,
            "error": str(e)
        }


# =============================================================================
# MASTER ORCHESTRATOR: Chapter → Production Package
# =============================================================================


def generate_chapter_production(story, chapter_narration, chapter_index, elements, 
                                 project_dir, break_text=None, progress_callback=None):
    """
    Master orchestrator: runs all 5 systems sequentially for one chapter.
    
    Pipeline:
    1. Cinematic Analyzer → storyboard table
    2. Scene State Tracker → JSON state per scene
    3. Visual Storyboard Chain → location images (or prompts for them)
    4. Scene Prompt Writer → video prompts per scene
    5. Add presenter break scenes (if break_text provided)
    
    Args:
        story: Complete story dict
        chapter_narration: The narration text for this chapter
        chapter_index: Which chapter (0-based)
        elements: List of element dicts
        project_dir: Path to project directory
        break_text: Optional presenter break text (appended as scenes after chapter)
        progress_callback: Optional callback
    
    Returns:
        Dict with all production data: storyboard, states, image_prompts, video_prompts
    """
    if progress_callback:
        progress_callback(f"🎬 === CHAPTER {chapter_index + 1} PRODUCTION PIPELINE ===", "info")
    
    char_name = story.get("character", {}).get("name", "protagonist")
    
    # =========================================================================
    # STEP 1: Cinematic Analysis
    # =========================================================================
    if progress_callback:
        progress_callback("📋 STEP 1/4: Cinematic Analysis...", "info")
    
    analysis = cinematic_analyze_chapter(
        story, chapter_narration, chapter_index, elements, progress_callback
    )
    storyboard = analysis.get("storyboard", [])
    
    if not storyboard:
        return {"error": "Cinematic analysis produced empty storyboard", "analysis": analysis}
    
    # Validate storyboard before proceeding
    if progress_callback:
        progress_callback("🔍 VALIDATION: Checking storyboard quality...", "info")
    
    validation = validate_storyboard(storyboard, chapter_narration, progress_callback)
    analysis["validation"] = validation
    
    if not validation["valid"]:
        if progress_callback:
            progress_callback(
                f"⚠️ Storyboard has {validation['total_errors']} error(s) — proceeding with warnings logged",
                "info"
            )
    
    # =========================================================================
    # STEP 2: State Tracking + Location Image Evaluation (sequential)
    # =========================================================================
    if progress_callback:
        progress_callback(f"📊 STEP 2/4: State Tracking ({len(storyboard)} scenes)...", "info")
    
    # Determine first location from storyboard
    first_loc = storyboard[0].get("location_id", "clearing") if storyboard else "clearing"
    state = init_scene_state(story, chapter_index, first_loc)
    
    all_states = []
    image_prompts = []
    
    for i, scene_row in enumerate(storyboard):
        # Evolve state
        new_state = evolve_scene_state(state, scene_row, progress_callback)
        
        # Evaluate location diff
        if i == 0:
            # First scene always needs an image
            diff = {"needs_new_image": True, "triggers": ["first_scene_in_chapter"]}
        else:
            diff = evaluate_location_diff(new_state, state)
        
        # Generate location image prompt if needed
        if diff["needs_new_image"]:
            img_prompt = generate_location_image_prompt(
                new_state, state if i > 0 else None, diff
            )
            new_state["location_image"] = img_prompt["output_filename"]
            image_prompts.append({
                "scene_num": scene_row.get("scene_num"),
                "image_prompt": img_prompt,
                "triggers": diff["triggers"]
            })
            if progress_callback:
                progress_callback(
                    f"  🖼️ Scene {scene_row['scene_num']}: NEW image → {img_prompt['output_filename']} "
                    f"({'from ref' if img_prompt['use_reference'] else 'standalone'})",
                    "batch"
                )
        else:
            # Reuse previous image
            new_state["location_image"] = state.get("location_image")
        
        all_states.append(new_state)
        state = new_state  # Pass forward
    
    if progress_callback:
        new_images = len(image_prompts)
        reused = len(storyboard) - new_images
        progress_callback(f"✅ State tracking done: {new_images} new images, {reused} reused", "success")
    
    # =========================================================================
    # STEP 3: Generate Location Images
    # =========================================================================
    if progress_callback:
        progress_callback(f"🖼️ STEP 3/4: Generating {len(image_prompts)} location images...", "info")
    
    locations_dir = os.path.join(project_dir, "locations")
    os.makedirs(locations_dir, exist_ok=True)
    
    generated_images = []
    for img_data in image_prompts:
        img_prompt = img_data["image_prompt"]
        output_path = os.path.join(locations_dir, img_prompt["output_filename"])
        
        try:
            if img_prompt["use_reference"] and img_prompt["reference_image"]:
                ref_path = os.path.join(locations_dir, img_prompt["reference_image"])
                if os.path.exists(ref_path):
                    generate_image_with_ref(
                        img_prompt["prompt"], output_path, ref_path
                    )
                else:
                    # Reference doesn't exist yet, generate standalone
                    generate_image(img_prompt["prompt"], output_path)
            else:
                generate_image(img_prompt["prompt"], output_path)
            
            generated_images.append(img_prompt["output_filename"])
            if progress_callback:
                progress_callback(f"  ✓ {img_prompt['output_filename']}", "success")
        except Exception as e:
            if progress_callback:
                progress_callback(
                    f"  ⚠️ {img_prompt['output_filename']} failed: {str(e)[:100]} — prompt saved for manual generation",
                    "error"
                )
    
    if progress_callback:
        progress_callback(f"✅ {len(generated_images)}/{len(image_prompts)} images generated", "success")
    
    # =========================================================================
    # STEP 4: Video Prompt Generation (per scene)
    # =========================================================================
    if progress_callback:
        progress_callback(f"✍️ STEP 4/4: Generating {len(storyboard)} video prompts...", "info")
    
    all_prompts = []
    for i, scene_row in enumerate(storyboard):
        scene_state = all_states[i]
        
        prompt_result = generate_video_prompt(
            scene_row, scene_state, elements, story,
            is_presenter=False, progress_callback=progress_callback
        )
        
        # Merge storyboard metadata into prompt result
        prompt_result["scene_num"] = scene_row.get("scene_num")
        prompt_result["type"] = scene_row.get("type")
        prompt_result["action"] = scene_row.get("action")
        prompt_result["narration_excerpt"] = scene_row.get("narration_excerpt")
        prompt_result["location_image"] = scene_state.get("location_image")
        prompt_result["bridge_reason"] = scene_row.get("bridge_reason")
        
        all_prompts.append(prompt_result)
        
        if progress_callback and (i + 1) % 3 == 0:
            progress_callback(f"  ... {i + 1}/{len(storyboard)} prompts done", "batch")
    
    # =========================================================================
    # BONUS: Presenter Break Scenes (if break_text provided)
    # =========================================================================
    if break_text:
        if progress_callback:
            progress_callback("🎙️ Adding presenter break scenes...", "info")
        
        # Count words to decide 1 or 2 scenes
        break_words = len(break_text.split())
        num_break_scenes = 2 if break_words > 30 else 1
        
        # Use the last chapter location for the presenter
        last_state = all_states[-1] if all_states else state
        last_scene_num = storyboard[-1].get("scene_num", 0) if storyboard else 0
        
        if num_break_scenes == 2:
            # Split narration roughly in half at a sentence boundary
            sentences = [s.strip() for s in break_text.replace("...", "…").split(".") if s.strip()]
            mid = len(sentences) // 2
            part_a = ". ".join(sentences[:mid]) + "."
            part_b = ". ".join(sentences[mid:])
            # Restore ellipses
            part_a = part_a.replace("…", "...")
            part_b = part_b.replace("…", "...")
            break_parts = [
                {"narration": part_a, "label": "Acknowledges what was done"},
                {"narration": part_b, "label": "Confronts what's coming"}
            ]
        else:
            break_parts = [{"narration": break_text, "label": "Presenter break"}]
        
        for j, part in enumerate(break_parts):
            break_scene_row = {
                "scene_num": last_scene_num + j + 1,
                "type": "presenter",
                "action": f"Presenter addresses camera: {part['label']}",
                "narration_excerpt": part["narration"],
                "elements": ["@Jack"],
                "location_id": last_state.get("location_id"),
                "time_of_day": last_state.get("time_of_day"),
                "weather": last_state.get("weather"),
                "tools": []
            }
            
            prompt_result = generate_video_prompt(
                break_scene_row, last_state, elements, story,
                is_presenter=True, progress_callback=progress_callback
            )
            prompt_result["scene_num"] = break_scene_row["scene_num"]
            prompt_result["type"] = "presenter"
            prompt_result["narration_excerpt"] = part["narration"]
            prompt_result["location_image"] = last_state.get("location_image")
            
            all_prompts.append(prompt_result)
        
        if progress_callback:
            progress_callback(f"✅ {num_break_scenes} presenter break scene(s) added", "success")
    
    # =========================================================================
    # ASSEMBLE PRODUCTION PACKAGE
    # =========================================================================
    total_duration = len(all_prompts) * 15  # 15s per scene
    
    production = {
        "chapter": chapter_index + 1,
        "analysis": analysis,
        "storyboard": storyboard,
        "states": all_states,
        "image_prompts": image_prompts,
        "generated_images": generated_images,
        "failed_images": [ip["image_prompt"]["output_filename"] for ip in image_prompts 
                          if ip["image_prompt"]["output_filename"] not in generated_images],
        "prompts": all_prompts,
        "metadata": {
            "total_scenes": len(all_prompts),
            "narrated_scenes": sum(1 for p in all_prompts if p.get("type") == "narrated"),
            "bridge_scenes": sum(1 for p in all_prompts if p.get("type") == "bridge"),
            "presenter_scenes": sum(1 for p in all_prompts if p.get("type") == "presenter"),
            "total_images_generated": len(generated_images),
            "total_images_needed": len(image_prompts),
            "estimated_duration_seconds": total_duration,
            "estimated_duration_formatted": f"{total_duration // 60}m {total_duration % 60}s"
        }
    }
    
    if progress_callback:
        m = production["metadata"]
        progress_callback(
            f"✅ CHAPTER {chapter_index + 1} COMPLETE: "
            f"{m['total_scenes']} scenes ({m['narrated_scenes']}N + {m['bridge_scenes']}B + {m['presenter_scenes']}P) = "
            f"~{m['estimated_duration_formatted']}",
            "success"
        )
    
    return production


def build_production_package(production, project_dir, chapter_index, progress_callback=None):
    """
    Save the production package to disk as organized files.
    
    Creates:
        projects/<id>/production/chapter_N/
        ├── prompts.json          # All scene prompts
        ├── storyboard.json       # Storyboard table
        ├── state_tracker.json    # All scene states
        ├── image_prompts.json    # Location image prompts (for manual generation fallback)
        └── assembly_notes.md     # Editor instructions
    
    Args:
        production: Output from generate_chapter_production()
        project_dir: Path to project directory
        chapter_index: Which chapter (0-based)
        progress_callback: Optional callback
    
    Returns:
        Path to the production package directory
    """
    chapter_dir = os.path.join(project_dir, "production", f"chapter_{chapter_index + 1}")
    os.makedirs(chapter_dir, exist_ok=True)
    
    # Save prompts
    with open(os.path.join(chapter_dir, "prompts.json"), "w") as f:
        json.dump(production.get("prompts", []), f, indent=2, ensure_ascii=False)
    
    # Save storyboard
    with open(os.path.join(chapter_dir, "storyboard.json"), "w") as f:
        json.dump(production.get("storyboard", []), f, indent=2, ensure_ascii=False)
    
    # Save state tracker
    with open(os.path.join(chapter_dir, "state_tracker.json"), "w") as f:
        json.dump(production.get("states", []), f, indent=2, ensure_ascii=False)
    
    # Save image prompts (for manual generation fallback)
    with open(os.path.join(chapter_dir, "image_prompts.json"), "w") as f:
        json.dump(production.get("image_prompts", []), f, indent=2, ensure_ascii=False)
    
    # Generate assembly notes
    analysis = production.get("analysis", {})
    metadata = production.get("metadata", {})
    
    notes = f"""# Chapter {chapter_index + 1} — Assembly Notes

## Overview
- **Process:** {analysis.get('process_understanding', 'N/A')}
- **Total scenes:** {metadata.get('total_scenes', 0)}
- **Narrated:** {metadata.get('narrated_scenes', 0)} | **Bridges:** {metadata.get('bridge_scenes', 0)} | **Presenter:** {metadata.get('presenter_scenes', 0)}
- **Estimated duration:** {metadata.get('estimated_duration_formatted', 'N/A')}

## Day Card Suggestions
"""
    for suggestion in analysis.get("day_card_suggestions", []):
        notes += f"- {suggestion}\n"
    
    notes += "\n## Failed Images (need manual generation)\n"
    for img in production.get("failed_images", []):
        notes += f"- {img} — see image_prompts.json for the prompt\n"
    if not production.get("failed_images"):
        notes += "- None — all images generated successfully\n"
    
    notes += "\n## Scene Sequence\n"
    notes += "| # | Type | Location Image | Action |\n"
    notes += "|---|------|---------------|--------|\n"
    for p in production.get("prompts", []):
        notes += f"| {p.get('scene_num', '?')} | {p.get('type', '?')} | {p.get('location_image', '?')} | {p.get('action', p.get('narration_excerpt', '?'))[:60]} |\n"
    
    with open(os.path.join(chapter_dir, "assembly_notes.md"), "w") as f:
        f.write(notes)
    
    if progress_callback:
        progress_callback(f"📦 Production package saved to: production/chapter_{chapter_index + 1}/", "success")
    
    return chapter_dir


# =============================================================================
# STEP: NARRATION GENERATION
# =============================================================================

def generate_narration(story, progress_callback=None):
    """
    Generate complete narration from story data following The Last Shelter style.
    
    Generates directly from story.narrative_arcs (no scenes needed):
    1. Presenter Intro — direct-to-camera intro with cinematic hook
    2. Phase narrations — continuous voice-over per narrative phase
    3. Presenter Breaks — cliffhanger transitions between acts
    4. Presenter Close — reflection + teaser
    
    Args:
        story: Complete story dict (must have narrative_arcs)
        progress_callback: Optional callback(message, type)
    
    Returns:
        Narration data dict
    """
    arcs = story.get("narrative_arcs", [])
    if not arcs:
        return {"error": "No narrative_arcs found in story"}
    
    char = story.get("character", {})
    char_name = char.get("name", "Unknown")
    location = story.get("location", {})
    construction = story.get("construction", {})
    timeline = story.get("timeline", {})
    conflicts = story.get("conflicts", [])
    duration = story.get("duration_minutes", 20)
    total_days = timeline.get("total_days", 42)
    
    # Build phases from narrative_arcs — each arc is one chapter
    original_chapters = [a["phase"] for a in arcs]
    
    # Build subdivided list: (phase_name, arc_data, original_chapter_name)
    # No scene subdivision needed — each arc is a natural chapter
    subdivided = [(a["phase"], a, a["phase"]) for a in arcs]
    
    # Dynamic word budget — 3000-3500 for 20 min (voiceover only, breaks excluded)
    WORD_BUDGET = {20: 3250, 15: 2400, 10: 1600, 5: 800}
    total_words = WORD_BUDGET.get(duration, 3250)
    
    # Distribute words proportionally to arc percentage
    for phase_name, arc, _ in subdivided:
        pct = arc.get("percentage", 100 // len(subdivided))
        arc["_word_budget"] = max(120, int(total_words * pct / 100))
    
    if progress_callback:
        progress_callback(f"🎙️ Generating narration for {len(subdivided)} phases ({len(original_chapters)} chapters)...", "info")
        progress_callback(f"📊 Target: ~{total_words} voiceover words, {len(original_chapters)-1} breaks", "info")
    
    # Build context string
    conflicts_text = "\n".join([f"- Day {c['day']}: {c['title']} — {c['description']}" for c in conflicts])
    
    # Build the character's emotional anchor for the narration
    char_motivation = char.get('motivation', 'to build')
    emotional_context = f"""CHARACTER'S EMOTIONAL ARC:
- Core Motivation: {char_motivation}
- The character's emotional goal must be THREADED through every phase of the narration.
- The INTRO establishes this goal. The RESOLUTION must CLOSE it explicitly.
"""

    narration_style = f"""NARRATION STYLE — The Last Shelter:
- Third person, present tense for action ("Erik drives the axe into frozen wood")
- Past tense for reflection and presenter breaks
- Raw, honest, visceral. Every word must earn its place.
- DEFAULT SENTENCE STYLE: CINEMATIC compound sentences (15-35 words). Layer sensory details with action and emotion in a single flowing line. EXAMPLE: "Elena's truck grinds to a halt as the thin air bites at her skin, a sharp chill that cuts through her jacket." NOT: "The truck stops. The air is thin. It's cold."
- REFLECTION moments: Even longer sentences (25-50 words), deeply introspective, connecting present action to the character's emotional goal.
- SHORT punchy sentences (5-12 words) are RESERVED for maximum-impact moments ONLY: turning points, crises, final lines of a phase. Use sparingly — no more than 2-3 per phase. They MUST contrast with the longer cinematic lines around them to create impact.
- Be SPECIFIC about sensations: don't say "the cold was brutal" — say "ice crystals form on the edges of his hood, each breath a cloud that freezes before it fades."
- Vocabulary variety: instead of always "cold" use freeze/chill/frost/ice. Instead of "silence" use stillness/quiet/void.
- NEVER describe visuals like camera directions. This is VOICEOVER, not stage directions.
- Include internal thoughts: "He wonders if he'll finish. Not someday. Today."
- EMOTIONAL HOOK: Every phase should connect the action to the character's emotional model (Future Vision, Primal Anchor, etc. depending on episode type). At least one line per phase should explicitly tie physical action to emotional motivation.

FUTURE VISION — SENSORY SPECIFICITY:
- When the character imagines or envisions their future/goal, describe it with CONCRETE sensory details.
- BAD (abstract): "He sees the future he's building, a primal anchor against the chaos."
- GOOD (concrete): "He closes his eyes and sees it clearly: smoke curling from the chimney, warm light spilling from the windows, a framed photograph of his father on the mantle—a tangible presence in this sanctuary he's building."
- The vision must include: specific objects, sounds, smells, textures. Make the reader SEE what the character sees.
- Connect the vision to the character's SPECIFIC emotional motivation ({char_motivation}).

THE ARON MOMENT — TURNING POINT:
- In the darkest, most desperate phase (highest tension crisis), there MUST be a moment of absolute clarity.
- This is the "Aron Moment" — like Aron Ralston seeing his future son before cutting his arm. The character sees their goal/loved one with vivid, unmistakable clarity.
- Pattern: Despair → Vision (crystal clear, specific, sensory-rich) → Transformed determination.
- The vision must be SO vivid the reader feels the warmth/presence. Use lines like: "And then, in the darkness, he sees it with absolute clarity."
- After the vision, the character's determination becomes UNSHAKABLE. Use a line like: "And in that moment, he knows with absolute certainty: he cannot fail."
- This moment should be 80-120 words — give it space to breathe and land emotionally.

EMOTIONAL ARC CLOSURE:
- The INTRO establishes the emotional hook (e.g., "chases a ghost", "honoring a memory").
- The RESOLUTION must explicitly MIRROR and CLOSE that hook.
- If intro says "chasing a ghost" → resolution must say "no longer chasing a ghost. He's honoring a memory."
- The final phase must include: a physical action that symbolizes completion (e.g., reaching for a photograph), a whispered line of dialogue, and a transformation statement.
"""

    
    # === STEP 1: PRESENTER INTRO ===
    if progress_callback:
        progress_callback("📢 Generating presenter intro...", "batch")
    
    intro_prompt = f"""{narration_style}

Generate the PRESENTER INTRO for The Last Shelter.

The PRESENTER (Jack Harlan) speaks DIRECTLY TO CAMERA as if he's on-location in the wilderness,
introducing this episode's story to the audience. He is energetic, confident, and commanding —
like a Bear Grylls or Alone-style host who is physically present at the location.

He introduces the CHARACTER and their challenge in a way that hooks the viewer immediately.
The tone is: survival reality TV show — urgent, cinematic, high-energy.

CHARACTER INFO:
- {char_name}, {char.get('age', 40)}, {char.get('profession', 'builder')} from {char.get('origin', 'unknown')}
- Motivation: {char.get('motivation', 'to build')}
- Location: {location.get('name', 'Unknown')}
- Timeline: {timeline.get('total_days', 42)} days. Deadline: {timeline.get('deadline_reason', 'winter')}
- Construction: {construction.get('type', 'Cabin')} ({construction.get('size_sqm', 30)} m²)

RULES:
1. FIRST PERSON as the PRESENTER talking to camera: "Today we're in..." / "Right now, down there..."
2. The presenter introduces THE CHARACTER in third person within his speech: "...an unemployed engineer named Erik..."
3. Hook immediately — action, urgency, stakes
4. Build tension with the deadline, extreme weather, and the character's personal stakes
5. End with a dramatic closer: "It starts now. This... is The Last Shelter."
6. Be 60-100 words. Punchy, dramatic rhythm. Every word must earn its place.
7. Use ellipses (...) for dramatic pauses
8. The text should feel like it's being SPOKEN aloud on-location, not read from a script

EXAMPLE of perfect tone:
"Today we're in the Yukon, Alaska! Down there, an unemployed engineer named Erik Lindqvist is about to attempt something incredible — build a log cabin from scratch before winter hits minus fifty! He's got 38 days before his father's birthday... and he's made a promise he can't break. It starts now. This... is The Last Shelter."

Return JSON:
{{
    "text": "The full presenter intro text",
    "duration_seconds": 30
}}"""
    
    try:
        intro = generate_json(intro_prompt, temperature=0.7, max_tokens=4000, model=GEMINI_MODEL_FLASH)
    except Exception as e:
        intro = {"text": story.get("presenter_intro", ""), "duration_seconds": 45}
        if progress_callback:
            progress_callback(f"⚠️ Intro fallback used: {e}", "error")
    
    if progress_callback:
        progress_callback(f"✅ Intro: {len(intro.get('text', '').split())} words", "success")
    
    # === STEP 2: PHASE NARRATIONS ===
    phase_narrations = []
    for idx, (phase_name, arc_data, orig_chapter) in enumerate(subdivided):
        if progress_callback:
            progress_callback(f"⏳ Phase {idx+1}/{len(subdivided)}: {phase_name}...", "batch")
        
        words_for_phase = arc_data.get("_word_budget", total_words // len(subdivided))
        arc_pct = arc_data.get("percentage", 100 // len(subdivided))
        arc_tension = arc_data.get("tension", 50)
        arc_desc = arc_data.get("description", phase_name)
        
        # Compute approximate day range for this arc
        cumulative_pct = sum(a.get("percentage", 0) for a in arcs[:idx])
        day_start = max(1, int(cumulative_pct / 100 * total_days) + 1)
        day_end = int((cumulative_pct + arc_pct) / 100 * total_days)
        
        # Find conflicts relevant to this day range
        phase_conflicts = [c for c in conflicts if day_start <= c.get("day", 0) <= day_end]
        phase_conflicts_text = "\n".join([
            f"- Day {c['day']}: {c['title']} — {c['description']}" for c in phase_conflicts
        ]) if phase_conflicts else "No major conflict in this phase."
        
        # Construction context
        construction_text = f"{construction.get('type', 'Cabin')} ({construction.get('size_sqm', 30)} m²)"
        
        # Determine if this is a turning point phase (highest tension crisis)
        is_turning_point = arc_tension >= 85
        is_resolution = idx == len(subdivided) - 1
        is_early_phase = idx <= 1  # First or second phase
        
        # Build phase-specific emotional instructions
        emotional_instructions = ""
        if is_early_phase:
            emotional_instructions = f"""
PHASE-SPECIFIC — FUTURE VISION:
This is an early phase. Include a moment where {char_name} visualizes the completed goal.
Describe the vision with CONCRETE sensory details: specific objects, sounds, smells.
Connect this vision directly to the character's core motivation: {char_motivation}.
Make the reader SEE what {char_name} sees in their mind's eye."""
        elif is_turning_point:
            emotional_instructions = f"""
PHASE-SPECIFIC — THE ARON MOMENT (CRITICAL):
This is the TURNING POINT — the darkest moment of the story (tension: {arc_tension}/100).
You MUST include the "Aron Moment":
1. Start with despair: {char_name} is at their lowest, questioning everything
2. Then: "And then, in the darkness, he/she sees it with absolute clarity."
3. A VIVID, SPECIFIC vision — the character sees their goal/loved one with unmistakable clarity.
   Include specific objects, dialogue, sensory details. Make it feel REAL.
4. The vision TRANSFORMS despair into unshakable determination.
5. End the vision with: "And in that moment... he/she knows with absolute certainty: he/she cannot fail."
6. Give this moment 80-120 words. Let it breathe. This is the emotional core of the entire story.
7. After the vision, the character's energy is DIFFERENT — burning, purposeful, unstoppable.
Character motivation to weave in: {char_motivation}."""
        elif is_resolution:
            emotional_instructions = f"""
PHASE-SPECIFIC — EMOTIONAL ARC CLOSURE (CRITICAL):
This is the FINAL phase. You MUST close the emotional arc completely:
1. Include a physical action that symbolizes completion (reaching for an object, touching a wall, etc.)
2. Include a whispered line of dialogue — the character speaking to themselves or to a loved one
3. Mirror the language from the intro: if the intro used words like "chasing a ghost" or "legacy",
   the resolution must TRANSFORM those words (e.g., "no longer chasing a ghost — honoring a memory")
4. End with a transformation statement: the character is HOME, not just in a shelter.
5. This is where the entire emotional arc pays off. Make the reader FEEL the journey's worth.
Character motivation to weave in: {char_motivation}."""
        else:
            emotional_instructions = f"""
PHASE-SPECIFIC:
Thread the character's emotional motivation ({char_motivation}) into the physical action.
At least one line should connect what {char_name} is doing with WHY — the deeper emotional goal."""
        
        phase_prompt = f"""{narration_style}

Generate CONTINUOUS NARRATION for phase "{phase_name}" of The Last Shelter.

Character: {char_name}, {char.get('age', 40)}
Companion: {char.get('companion', {}).get('name', 'Dog')} ({char.get('companion', {}).get('breed', 'mixed')})
Location: {location.get('name', 'Unknown')}
Construction: {construction_text}

WHAT HAPPENS IN THIS PHASE:
{arc_desc}
Days: {day_start}-{day_end} of {total_days}
Tension level: {arc_tension}/100
Percentage of total story: {arc_pct}%

CONFLICTS IN THIS PHASE:
{phase_conflicts_text}
{emotional_instructions}

RULES:
1. Write EXACTLY ~{words_for_phase} words of continuous narration covering this phase
2. Write FLOWING narration that covers the events naturally
3. Include sensory details: sounds, temperature, physical sensations
4. If a conflict happens in this phase, build tension around it
5. The companion animal should appear naturally — describe specific actions (leaping, sniffing, watching, etc.)
6. Use PARAGRAPH BREAKS (\\n\\n) to separate distinct moments or beats. Each paragraph should be 3-5 sentences. NEVER write a single wall of text.
7. WORD LIMIT IS STRICT: stay within {words_for_phase - 30} to {words_for_phase + 30} words
8. Follow the PHASE-SPECIFIC emotional instructions above — they are CRITICAL for quality.

Return JSON:
{{
    "phase_name": "{phase_name}",
    "narration": "The full narration text with \\n\\n paragraph breaks",
    "word_count": {words_for_phase}
}}"""
        
        try:
            phase_result = generate_json(phase_prompt, temperature=0.7, max_tokens=4000, model=GEMINI_MODEL_FLASH)
            phase_narrations.append(phase_result)
            if progress_callback:
                wc = phase_result.get("word_count", len(phase_result.get("narration", "").split()))
                progress_callback(f"✓ {phase_name}: {wc} words", "success")
        except Exception as e:
            # Retry up to 2 times
            retried = False
            for attempt in range(2):
                if progress_callback:
                    progress_callback(f"⚠️ Retry {attempt+1}/2 for {phase_name}...", "warning")
                try:
                    import time as _time
                    _time.sleep(2)
                    phase_result = generate_json(phase_prompt, temperature=0.6, max_tokens=3000, model=GEMINI_MODEL_FLASH)
                    phase_narrations.append(phase_result)
                    if progress_callback:
                        wc = phase_result.get("word_count", len(phase_result.get("narration", "").split()))
                        progress_callback(f"✓ {phase_name}: {wc} words (retry {attempt+1})", "success")
                    retried = True
                    break
                except Exception:
                    pass
            if not retried:
                if progress_callback:
                    progress_callback(f"❌ Failed {phase_name} after retries: {e}", "error")
                # Insert placeholder so partial narration can still be saved
                phase_narrations.append({
                    "phase_name": phase_name,
                    "narration": f"[Narration for {phase_name} failed to generate — regenerate to retry]",
                    "word_count": 0,
                    "error": str(e)
                })
    
    # === STEP 3: PRESENTER BREAKS (one per chapter boundary) ===
    if progress_callback:
        progress_callback(f"📢 Generating {len(original_chapters)-1} presenter breaks (1 per chapter)...", "batch")
    
    breaks = []
    # Build a map: which sub-phase indices end each original chapter
    chapter_end_indices = {}  # {chapter_name: last_sub_phase_index}
    for idx, (_, _, orig_chapter) in enumerate(subdivided):
        chapter_end_indices[orig_chapter] = idx
    
    # Generate a break after each chapter (except the last)
    for ch_idx, chapter_name in enumerate(original_chapters[:-1]):
        after_sub_idx = chapter_end_indices[chapter_name]
        next_chapter = original_chapters[ch_idx + 1]
        
        # Find relevant conflict for this transition
        relevant_conflict = ""
        for c in conflicts:
            c_title = c.get('title', '')
            if c_title.lower() in chapter_name.lower() or c_title.lower() in next_chapter.lower():
                relevant_conflict = f"KEY EVENT: {c_title} — {c.get('description', '')}"
                break
        
        if progress_callback:
            progress_callback(f"📢 Break {ch_idx+1}/{len(original_chapters)-1}: after {chapter_name}...", "batch")
        
        break_prompt = f"""
Generate a PRESENTER BREAK (cliffhanger) for The Last Shelter.
Style: AGGRESSIVE, direct, confrontational. Like a sports commentator calling the action.
Short punchy sentences that HIT. Use ellipses sparingly for dramatic pauses.

This is delivered directly to camera by the presenter between chapters.
The viewer just finished watching: "{chapter_name}"
What's coming next: "{next_chapter}"
{relevant_conflict}

STORY CONTEXT:
- {char_name} is building a {construction.get('type', 'cabin')} in {location.get('name', 'the wilderness')}
- Timeline: {timeline.get('total_days', 42)} days

RULES:
1. ALWAYS name {char_name} — never say "he" without naming him first
2. ACKNOWLEDGE what {char_name} just accomplished — be specific: "chose his ground", "dropped thirty trees", "got the walls chest-high"
3. Then CONFRONT with what's coming — the Yukon doesn't care, winter doesn't wait
4. Be AGGRESSIVE and DIRECT, not poetic or mysterious. Punchy. Confrontational.
5. Be 30-50 words. Every sentence lands like a punch.
6. Reference SPECIFIC details from what just happened and what's ahead
7. End with a gut-punch line — short, brutal, final
8. Think sports commentator meets war correspondent, NOT a poet

Examples of PERFECT breaks:
- "{char_name} chose his ground. Cleared it. Staked it. Claimed it. But the Yukon doesn't care about claims. Thirty-eight days. Hundreds of trees. And every... single... one... has to come down. By hand."
- "{char_name} dropped thirty trees in four days. Stripped them. Stacked them. But a log cabin needs walls. And walls need notches. Perfect notches. One mistake... and the whole thing comes apart."
- "Three weeks in. {char_name}'s got walls. He's got a roof frame. He's ahead of schedule. Then the temperature drops to minus forty... and everything changes."

Return JSON:
{{
    "text": "The break text",
    "after_phase_index": {after_sub_idx},
    "after_chapter": "{chapter_name}",
    "before_chapter": "{next_chapter}",
    "duration_seconds": 25
}}"""
        
        try:
            break_result = generate_json(break_prompt, temperature=0.8, max_tokens=4000, model=GEMINI_MODEL_FLASH)
            breaks.append(break_result)
            if progress_callback:
                progress_callback(f"✓ Break after '{chapter_name}': {len(break_result.get('text', '').split())} words", "success")
        except Exception as e:
            if progress_callback:
                progress_callback(f"⚠️ Break after '{chapter_name}' failed: {e}", "error")
    
    if progress_callback:
        progress_callback(f"✅ {len(breaks)} presenter breaks generated", "success")
    
    # === STEP 4: PRESENTER CLOSE ===
    if progress_callback:
        progress_callback("🎬 Generating presenter close...", "batch")
    
    # Get the intro text to reference for arc closure
    intro_text = intro.get('text', '')
    
    close_prompt = f"""
Generate the PRESENTER OUTRO for The Last Shelter.
Style: raw, honest, visceral. Short punchy sentences. Third person.

The presenter reflects on {char_name}'s journey. Campfire setting. Night.
The construction is complete. The character succeeded (or survived).
Character's core motivation: {char_motivation}

INTRO TEXT (for arc closure):
"{intro_text}"

The close must:
1. Reflect on the journey — what was really built (beyond the physical structure)
2. MIRROR AND CLOSE the emotional arc from the intro. If the intro used specific language
   (e.g., "chases a ghost", "a promise to his wife", "legacy"), the outro MUST reference
   and TRANSFORM those exact words. This creates a satisfying emotional payoff.
3. Be emotional but not sentimental — raw and earned
4. Include at least one line about what the character REALLY built (not just the structure)
5. End with a teaser for the next episode (make one up)
6. Be 60-100 words

Return JSON:
{{
    "text": "The close text",
    "teaser": "Next time on The Last Shelter... one sentence preview",
    "duration_seconds": 35
}}"""
    
    try:
        close = generate_json(close_prompt, temperature=0.7, max_tokens=4000, model=GEMINI_MODEL_FLASH)
    except Exception as e:
        close = {"text": story.get("presenter_close", ""), "teaser": "", "duration_seconds": 35}
        if progress_callback:
            progress_callback(f"⚠️ Close fallback: {e}", "error")
    
    # Assemble final narration
    voiceover_words = sum(p.get("word_count", len(p.get("narration", "").split())) for p in phase_narrations)
    breaks_words = sum(len(b.get("text", "").split()) for b in breaks)
    intro_words = len(intro.get("text", "").split())
    close_words = len(close.get("text", "").split())
    total_word_count = voiceover_words + breaks_words + intro_words + close_words
    
    narration = {
        "intro": intro,
        "phases": phase_narrations,
        "breaks": breaks,
        "close": close,
        "summary": {
            "total_words": total_word_count,
            "voiceover_words": voiceover_words,
            "breaks_words": breaks_words + intro_words + close_words,
            "phases_count": len(phase_narrations),
            "breaks_count": len(breaks),
            "chapters_count": len(original_chapters),
        }
    }
    
    if progress_callback:
        progress_callback(f"✅ Narration complete: {total_word_count} words, {len(phase_narrations)} phases, {len(breaks)} breaks", "success")
    
    return narration
