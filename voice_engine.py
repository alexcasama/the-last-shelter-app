"""
The Last Shelter — Voice Engine (ElevenLabs v3)

Generates emotional TTS audio from narration text using ElevenLabs v3.
Uses Gemini Flash to inject audio tags ([sighs], [whispers], [excited], etc.)
before sending to ElevenLabs for maximum expressiveness.

Pipeline:
1. enhance_narration_for_tts() — Gemini adds audio tags + expressive punctuation
2. generate_audio_segment() — ElevenLabs v3 TTS for a single segment
3. generate_all_audio() — Full pipeline: intro → phases → breaks → close
"""
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIG
# =============================================================================

ELEVENLABS_MODEL = "eleven_v3"
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_SPEED = 0.70

# Gemini model for enhancing narration with audio tags
GEMINI_MODEL_FLASH = "gemini-2.5-flash"

# =============================================================================
# ENHANCE NARRATION — Gemini injects ElevenLabs v3 audio tags
# =============================================================================

ENHANCE_PROMPT = """You are an AI assistant specializing in enhancing narration text for ElevenLabs v3 text-to-speech.

Your PRIMARY GOAL is to dynamically integrate audio tags and expressive punctuation into the narration, making it more emotional and human-sounding for speech generation, while STRICTLY preserving the original text and meaning.

## AUDIO TAGS (ElevenLabs v3)
These tags go in square brackets and control vocal delivery:

**Emotional delivery:**
- [sighs] — weariness, sadness, resignation
- [exhales] — relief, exhaustion, contemplation
- [whispers] — intimacy, tension, secrets
- [excited] — enthusiasm, breakthrough moments
- [curious] — questioning, wonder
- [sad] — grief, loss moments
- [thoughtful] — reflection, memory
- [angry] — frustration, fury

**Non-verbal:**
- [short pause] — brief beat
- [long pause] — dramatic beat
- [inhales deeply] — before important statements
- [clears throat] — transitions

## PUNCTUATION TECHNIQUES
- Ellipses (…) add weight and pauses: "It was… quiet."
- CAPS for emphasis on key words: "It was VERY cold."
- Em dashes (—) for abrupt shifts: "He reached for the axe—then stopped."

## RULES
1. DO NOT alter, add, or remove any words from the original narration text
2. Only ADD audio tags and adjust punctuation (caps, ellipses, em dashes)
3. Audio tags go BEFORE the phrase they modify, or AFTER for reactions
4. Use tags SPARINGLY — max 2-4 per paragraph. Over-tagging sounds unnatural
5. Match tags to the emotional context of the text
6. For The Last Shelter style: favor [sighs], [exhales], [whispers], [inhales deeply] — raw, visceral narration
7. DO NOT add tags for sound effects (no [wind], [crackle], etc.) — voice only
8. DO NOT wrap original text in brackets

## SEGMENT TYPE: {segment_type}
## TENSION LEVEL: {tension}/100

{type_specific_instructions}

## INPUT TEXT:
{text}

## OUTPUT:
Return ONLY the enhanced text with audio tags and punctuation adjustments. No explanations, no JSON wrapping.
"""

TYPE_INSTRUCTIONS = {
    "narration": """This is VOICEOVER narration — third person, cinematic, visceral.
- Use [sighs] and [exhales] for moments of exhaustion or contemplation
- Use [whispers] for intimate internal thoughts
- Use [inhales deeply] before critical revelations
- Increase intensity of tags as tension climbs
- At tension > 80: more CAPS, shorter pauses, [exhales sharply]
- At tension < 30: softer delivery, [thoughtful], longer pauses with ellipses""",

    "intro": """This is the PRESENTER INTRO — direct to camera, dramatic hook.
- Start with [inhales deeply] or [clears throat] for presence
- Use ellipses for dramatic build-up
- CAPS on the most dramatic word in the hook
- End with a strong, clear delivery — no trailing tags
- Keep tags minimal (2-3 max) — let the words carry the weight""",

    "break": """This is a PRESENTER BREAK — cliffhanger between chapters.
- Maximum tension. Use [whispers] for ominous hints
- Use [long pause] between key revelations
- CAPS on the twist word
- Ellipses before the final line for suspense
- Keep it tight — these are 30-50 words, so 1-2 tags max""",

    "close": """This is the PRESENTER CLOSE — emotional reflection at the end.
- Use [sighs] or [exhales] for earned emotion
- Use [thoughtful] for the reflection moment
- Softer delivery than the intro — the journey is over
- End with quiet confidence — the last line should land clean
- 2-3 tags max""",
}


def enhance_narration_for_tts(text, segment_type="narration", tension_level=50):
    """
    Use Gemini Flash to inject ElevenLabs v3 audio tags into narration text.
    
    Args:
        text: Original narration text
        segment_type: "narration", "intro", "break", or "close"
        tension_level: 0-100, affects intensity of emotional tags
    
    Returns:
        Enhanced text with audio tags and expressive punctuation
    """
    from google import genai
    from google.genai import types
    
    client = genai.Client()
    
    type_instructions = TYPE_INSTRUCTIONS.get(segment_type, TYPE_INSTRUCTIONS["narration"])
    
    prompt = ENHANCE_PROMPT.format(
        segment_type=segment_type.upper(),
        tension=tension_level,
        type_specific_instructions=type_instructions,
        text=text,
    )
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_FLASH,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=4000,
            ),
        )
        enhanced = response.text.strip()
        
        # Clean up any markdown wrapping that Gemini might add
        if enhanced.startswith("```"):
            lines = enhanced.split("\n")
            enhanced = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        
        # Strip quotes if wrapped
        if enhanced.startswith('"') and enhanced.endswith('"'):
            enhanced = enhanced[1:-1]
        
        return enhanced
    
    except Exception as e:
        print(f"[Voice Engine] Enhancement failed, using original text: {e}")
        return text


# =============================================================================
# GENERATE AUDIO — ElevenLabs v3 TTS
# =============================================================================

def generate_audio_segment(text, voice_id, output_path, previous_request_ids=None, speed=None):
    """
    Generate a single audio segment using ElevenLabs v3.
    
    Args:
        text: Text to convert (should be pre-enhanced with audio tags)
        voice_id: ElevenLabs voice ID
        output_path: Where to save the MP3 file
        previous_request_ids: List of previous request IDs for continuity stitching
        speed: Speech speed (0.7-1.2, default 1.0)
    
    Returns:
        Dict with path, duration_seconds, file_size
    """
    from elevenlabs.client import ElevenLabs
    from elevenlabs.types import VoiceSettings
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not set in environment")
    
    client = ElevenLabs(api_key=api_key)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Voice settings — tuned via A/B testing
    # v3 stability: 0.0 (Creative), 0.5 (Natural), 1.0 (Robust)
    # Natural = best balance of expressiveness + clarity for narration
    voice_settings = VoiceSettings(
        stability=0.5,
        speed=speed or DEFAULT_SPEED,
    )
    
    # Build kwargs
    kwargs = {
        "text": text,
        "voice_id": voice_id,
        "model_id": ELEVENLABS_MODEL,
        "output_format": ELEVENLABS_OUTPUT_FORMAT,
        "voice_settings": voice_settings,
    }
    
    if previous_request_ids:
        kwargs["previous_request_ids"] = previous_request_ids[-3:]  # Max 3
    
    # Generate audio (returns iterator of bytes)
    audio_iterator = client.text_to_speech.convert(**kwargs)
    
    # Collect all chunks and write to file
    audio_bytes = b""
    for chunk in audio_iterator:
        audio_bytes += chunk
    
    with open(output_path, "wb") as f:
        f.write(audio_bytes)
    
    # Estimate duration from file size (MP3 128kbps ≈ 16KB/s)
    file_size = os.path.getsize(output_path)
    duration_seconds = round(file_size / 16000, 1)
    
    return {
        "path": output_path,
        "duration_seconds": duration_seconds,
        "file_size": file_size,
    }


# =============================================================================
# FULL PIPELINE — Generate all audio from narration
# =============================================================================

def generate_all_audio(narration, project_dir, voice_id, progress_callback=None):
    """
    Generate all audio segments from complete narration data.
    
    Processes in order: intro → (phase + break pairs) → close.
    Uses previous_request_ids for continuity between consecutive segments.
    
    Args:
        narration: Complete narration dict (from generate_narration())
        project_dir: Project directory path
        voice_id: ElevenLabs voice ID
        progress_callback: Optional callback(message, type)
    
    Returns:
        Dict with segments list and audio_manifest
    """
    audio_dir = os.path.join(project_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    
    segments = []
    total_segments = 1 + len(narration.get("phases", [])) + len(narration.get("breaks", [])) + 1
    current = 0
    
    def gen_segment(text, segment_type, filename, tension=50):
        nonlocal current
        current += 1
        
        if progress_callback:
            progress_callback(
                f"🔊 [{current}/{total_segments}] Generating {segment_type}: {filename}...",
                "batch"
            )
        
        # Step 1: Enhance text with audio tags
        enhanced_text = enhance_narration_for_tts(text, segment_type, tension)
        
        if progress_callback:
            # Show a preview of the enhancement
            tag_count = enhanced_text.count("[")
            progress_callback(f"  ✨ Enhanced: {tag_count} audio tags added", "info")
        
        # Step 2: Generate audio
        output_path = os.path.join(audio_dir, filename)
        
        result = generate_audio_segment(
            enhanced_text, voice_id, output_path,
        )
        
        segment_data = {
            "type": segment_type,
            "filename": filename,
            "original_text": text,
            "enhanced_text": enhanced_text,
            "duration_seconds": result["duration_seconds"],
            "file_size": result["file_size"],
        }
        segments.append(segment_data)
        
        if progress_callback:
            progress_callback(
                f"  ✅ {filename}: {result['duration_seconds']}s ({result['file_size'] // 1024}KB)",
                "success"
            )
        
        # Rate limiting — be respectful to API
        time.sleep(0.5)
        
        return segment_data
    
    # === INTRO ===
    intro = narration.get("intro", {})
    if intro.get("text"):
        gen_segment(intro["text"], "intro", "intro.mp3", tension=40)
    
    # === PHASES + BREAKS (interleaved) ===
    phases = narration.get("phases", [])
    breaks = narration.get("breaks", [])
    
    for i, phase in enumerate(phases):
        phase_text = phase.get("narration", "")
        if not phase_text or phase_text.startswith("[Narration for"):
            continue
        
        phase_name = phase.get("phase_name", f"phase_{i+1}")
        # Estimate tension from position in story
        tension = min(95, 20 + (i / max(1, len(phases) - 1)) * 70)
        
        gen_segment(phase_text, "narration", f"phase_{i+1}.mp3", tension=tension)
        
        # Insert break after this phase if one exists
        if i < len(breaks):
            break_text = breaks[i].get("text", "")
            if break_text:
                gen_segment(break_text, "break", f"break_{i+1}.mp3", tension=85)
    
    # === CLOSE ===
    close = narration.get("close", {})
    if close.get("text"):
        close_text = close["text"]
        # Append teaser if exists
        teaser = close.get("teaser", "")
        if teaser:
            close_text += f" {teaser}"
        gen_segment(close_text, "close", "close.mp3", tension=25)
    
    # === SAVE MANIFEST ===
    total_duration = sum(s["duration_seconds"] for s in segments)
    manifest = {
        "voice_id": voice_id,
        "model": ELEVENLABS_MODEL,
        "total_segments": len(segments),
        "total_duration_seconds": round(total_duration, 2),
        "total_duration_formatted": f"{int(total_duration // 60)}m {int(total_duration % 60)}s",
        "segments": segments,
    }
    
    manifest_path = os.path.join(audio_dir, "audio_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    if progress_callback:
        progress_callback(
            f"✅ Audio complete: {len(segments)} segments, "
            f"~{int(total_duration // 60)}m {int(total_duration % 60)}s total",
            "success"
        )
    
    return manifest
