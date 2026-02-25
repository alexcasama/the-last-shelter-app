"""
The Last Shelter — Flask Application
Single-page app for generating stories, scenes, and images for G-Labs.
"""
import os
import json
import time
import uuid
import threading
from pathlib import Path

from flask import Flask, render_template, request, jsonify, Response, send_from_directory, send_file
from dotenv import load_dotenv

import story_engine
import diversity_tracker
import script_parser
import script_breakdown

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tls-dev-key-2026")

# Project storage
# If we are in Production on Railway and the /app/data Volume exists, use it. Otherwise, use local.
vol_proj_path = Path("/app/data/projects")
if os.environ.get("FLASK_ENV") == "production" and vol_proj_path.parent.exists():
    PROJECTS_DIR = vol_proj_path
else:
    PROJECTS_DIR = Path(__file__).parent / "projects"
    
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# SSE progress streams (per project)
_progress_streams = {}


# =============================================================================
# HELPERS
# =============================================================================

def get_project_dir(project_id):
    """Get or create project directory."""
    d = PROJECTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_project_metadata(project_id):
    """Load project metadata.json."""
    meta_path = get_project_dir(project_id) / "metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            return json.load(f)
    return {}


def save_project_metadata(project_id, data):
    """Save project metadata.json."""
    meta_path = get_project_dir(project_id) / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def progress_callback_factory(project_id):
    """Create a progress callback that pushes to SSE stream."""
    def callback(message, msg_type="info"):
        if project_id in _progress_streams:
            _progress_streams[project_id].append({
                "message": message,
                "type": msg_type,
                "timestamp": time.time()
            })
    return callback


# =============================================================================
# ROUTES — Pages
# =============================================================================

@app.route("/")
def index():
    """Main single-page app."""
    # List existing projects
    projects = []
    if PROJECTS_DIR.exists():
        for d in sorted(PROJECTS_DIR.iterdir(), reverse=True):
            if d.is_dir():
                meta = load_project_metadata(d.name)
                if meta:
                    projects.append({
                        "id": d.name,
                        "title": meta.get("title", "Untitled"),
                        "created": meta.get("created_at", ""),
                        "status": meta.get("status", "new"),
                        "duration": meta.get("duration_minutes", 20),
                        "episode_type": meta.get("episode_type", "build"),
                    })
    return render_template("index.html", projects=projects)


@app.route("/storyboard/<project_id>")
def storyboard_view(project_id):
    """Full-screen storyboard grid view."""
    meta = load_project_metadata(project_id)
    if not meta:
        return "Project not found", 404
    return render_template("storyboard.html", project_id=project_id, project_title=meta.get("title", "Untitled"))


@app.route("/api/project/<project_id>/location/<path:filepath>")
def serve_location_image(project_id, filepath):
    """Serve a location reference image from production folder."""
    project_dir = get_project_dir(project_id)
    return send_from_directory(project_dir / "production", filepath)


# =============================================================================
# ROUTES — API
# =============================================================================

@app.route("/api/project/create", methods=["POST"])
def create_project():
    """Create a new project with title and optional script upload."""
    # Support both JSON and multipart/form-data
    if request.content_type and 'multipart/form-data' in request.content_type:
        title = request.form.get("title", "").strip()
        script_file = request.files.get("script")
    else:
        data = request.json or {}
        title = data.get("title", "").strip()
        script_file = None
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
    
    project_id = str(uuid.uuid4())[:8] + "-" + title.lower().replace(" ", "-")[:30]
    
    metadata = {
        "id": project_id,
        "title": title,
        "status": "created",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "steps_completed": []
    }
    
    save_project_metadata(project_id, metadata)
    
    # If script file provided, parse it immediately
    if script_file and script_file.filename:
        project_dir = get_project_dir(project_id)
        
        # Save raw script
        raw_content = script_file.read().decode("utf-8")
        with open(project_dir / "script_raw.md", "w") as f:
            f.write(raw_content)
        
        # Parse script
        parsed = script_parser.parse_script(raw_content)
        with open(project_dir / "script.json", "w") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        
        # Update metadata
        metadata["status"] = "script_uploaded"
        metadata["steps_completed"].append("script")
        if parsed.get("total_duration"):
            metadata["duration"] = parsed["total_duration"]
        save_project_metadata(project_id, metadata)
    
    return jsonify({"project_id": project_id, "metadata": metadata})


@app.route("/api/project/<project_id>")
def get_project(project_id):
    """Get full project data."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    project_dir = get_project_dir(project_id)
    
    # Load parsed script if exists
    script_path = project_dir / "script.json"
    script = None
    if script_path.exists():
        with open(script_path) as f:
            script = json.load(f)
    
    # Load story if exists
    story_path = project_dir / "story.json"
    story = None
    if story_path.exists():
        with open(story_path) as f:
            story = json.load(f)
    
    # Load narration if exists
    narration_path = project_dir / "narration.json"
    narration = None
    if narration_path.exists():
        with open(narration_path) as f:
            narration = json.load(f)
    
    # Load elements if exists
    elements_path = project_dir / "elements.json"
    elements = None
    if elements_path.exists():
        with open(elements_path) as f:
            elements = json.load(f)
    
    # Check for element images
    elements_dir = project_dir / "elements"
    element_images = []
    if elements_dir.exists():
        element_images = [f"/api/project/{project_id}/element/{f.name}" 
                         for f in sorted(elements_dir.iterdir()) if f.suffix in ('.png', '.jpg', '.webp')]
    
    # Load scene prompts if exists
    scene_prompts_path = project_dir / "scene_prompts.json"
    scene_prompts = None
    if scene_prompts_path.exists():
        with open(scene_prompts_path) as f:
            scene_prompts = json.load(f)
    
    # Load quality report if exists
    quality_path = project_dir / "quality_report.json"
    quality_report = None
    if quality_path.exists():
        with open(quality_path) as f:
            quality_report = json.load(f)
    
    # Load audio manifest if exists
    audio_manifest_path = project_dir / "audio" / "manifest.json"
    audio_manifest = None
    if audio_manifest_path.exists():
        with open(audio_manifest_path) as f:
            audio_manifest = json.load(f)
    
    return jsonify({
        "metadata": meta,
        "script": script,
        "story": story,
        "narration": narration,
        "elements": elements,
        "element_images": element_images,
        "scene_prompts": scene_prompts,
        "quality_report": quality_report,
        "audio_manifest": audio_manifest,
    })


@app.route("/api/project/<project_id>/upload-script", methods=["POST"])
def api_upload_script(project_id):
    """Upload or re-upload a script .md file to an existing project."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    script_file = request.files.get("script")
    if not script_file or not script_file.filename:
        return jsonify({"error": "No script file provided"}), 400
    
    project_dir = get_project_dir(project_id)
    
    # Save raw script
    raw_content = script_file.read().decode("utf-8")
    with open(project_dir / "script_raw.md", "w") as f:
        f.write(raw_content)
    
    # Parse script
    parsed = script_parser.parse_script(raw_content)
    with open(project_dir / "script.json", "w") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)
    
    # Update metadata
    meta["status"] = "script_uploaded"
    if "script" not in meta.get("steps_completed", []):
        meta.setdefault("steps_completed", []).append("script")
    if parsed.get("total_duration"):
        meta["duration"] = parsed["total_duration"]
    save_project_metadata(project_id, meta)
    
    return jsonify({"status": "ok", "script": parsed})


@app.route("/api/project/<project_id>/element/<filename>")
def serve_element(project_id, filename):
    """Serve an element reference image."""
    elements_dir = get_project_dir(project_id) / "elements"
    return send_from_directory(elements_dir, filename)


@app.route("/api/project/<project_id>/frame/<filename>")
def serve_frame(project_id, filename):
    """Serve a Frame A image."""
    frames_dir = get_project_dir(project_id) / "frames"
    return send_from_directory(frames_dir, filename)


@app.route("/api/project/<project_id>/audio/<filename>")
def serve_audio(project_id, filename):
    """Serve a generated audio file."""
    audio_dir = get_project_dir(project_id) / "audio"
    return send_from_directory(audio_dir, filename)


@app.route("/api/project/<project_id>/audio_zip")
def serve_audio_zip(project_id):
    """Download all generated audio files as a ZIP."""
    import zipfile
    import io

    audio_dir = get_project_dir(project_id) / "audio"
    if not audio_dir.exists():
        return jsonify({"error": "No audio files"}), 404

    mp3_files = sorted(audio_dir.glob("*.mp3"))
    if not mp3_files:
        return jsonify({"error": "No audio files"}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in mp3_files:
            zf.write(f, f.name)
    buf.seek(0)

    meta = load_project_metadata(project_id)
    title = (meta.get("title") or project_id).replace(" ", "_")
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True,
                     download_name=f"{title}_audio.zip")


@app.route("/api/project/<project_id>/generate_audio_segment", methods=["POST"])
def api_generate_audio_segment(project_id):
    """Generate TTS audio for a single narration segment."""
    from voice_engine import enhance_narration_for_tts, generate_audio_segment
    
    project_dir = get_project_dir(project_id)
    data = request.json
    
    segment_id = data.get("segment_id")
    segment_type = data.get("segment_type", "narration")
    voice_id = data.get("voice_id")
    model = data.get("model", "eleven_v3")
    speed = data.get("speed", 0.70)
    stability = data.get("stability", 0.5)
    
    if not voice_id:
        return jsonify({"error": "voice_id is required"}), 400
    
    # Load narration to find the text
    narration_path = project_dir / "narration.json"
    if not narration_path.exists():
        return jsonify({"error": "Narration not found"}), 404
    
    with open(narration_path) as f:
        narration = json.load(f)
    
    # Find the text for this segment
    text = None
    if segment_id == "intro":
        text = (narration.get("intro") or {}).get("text", "")
    elif segment_id == "close":
        close = narration.get("close") or {}
        text = close.get("text", "")
        if close.get("teaser"):
            text += "\n\n" + close["teaser"]
    elif segment_id.startswith("chapter_"):
        idx = int(segment_id.split("_")[1])
        phases = narration.get("phases", [])
        if idx < len(phases):
            text = phases[idx].get("narration", "")
    elif segment_id.startswith("break_"):
        idx = int(segment_id.split("_")[1])
        breaks = narration.get("breaks", [])
        brk = next((b for b in breaks if b.get("after_phase_index") == idx), None)
        if brk:
            text = brk.get("text", "")
    
    if not text:
        return jsonify({"error": f"Could not find text for segment '{segment_id}'"}), 404
    
    try:
        # Step 1: Enhance text with audio tags
        tension = 50
        if segment_type == "break":
            tension = 80
        elif segment_type == "intro":
            tension = 70
        elif segment_type == "close":
            tension = 40
        
        enhanced_text = enhance_narration_for_tts(text, segment_type=segment_type, tension_level=tension)
        
        # Step 2: Generate audio
        audio_dir = project_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        
        filename = f"{segment_id}.mp3"
        output_path = audio_dir / filename
        
        # Load previous request IDs for continuity
        manifest_path = audio_dir / "manifest.json"
        manifest = {}
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
        
        previous_ids = []
        # Find the previous segment's request IDs for continuity
        # (segments are ordered: intro, chapter_0, break_0, chapter_1, break_1, ...)
        
        result = generate_audio_segment(
            text=enhanced_text,
            voice_id=voice_id,
            output_path=str(output_path),
            previous_request_ids=previous_ids if previous_ids else None,
            speed=speed
        )
        
        # Update manifest
        manifest[segment_id] = {
            "filename": filename,
            "duration_seconds": result.get("duration_seconds"),
            "file_size": result.get("file_size"),
            "request_id": result.get("request_id"),
            "segment_type": segment_type,
            "enhanced_text": enhanced_text[:500]  # Store first 500 chars for reference
        }
        
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        return jsonify({
            "filename": filename,
            "duration_seconds": result.get("duration_seconds"),
            "file_size": result.get("file_size"),
            "segment_id": segment_id
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/project/<project_id>/regenerate-frame/<int:scene_number>", methods=["POST"])
def api_regenerate_frame(project_id, scene_number):
    """Regenerate Frame A image for a specific scene."""
    project_dir = get_project_dir(project_id)
    sp_path = project_dir / "scene_prompts.json"
    if not sp_path.exists():
        return jsonify({"error": "Scene prompts not found"}), 404
    
    with open(sp_path) as f:
        scene_prompts = json.load(f)
    
    scenes = scene_prompts.get("scenes", [])
    scene = next((s for s in scenes if s.get("number") == scene_number), None)
    if not scene:
        return jsonify({"error": f"Scene {scene_number} not found"}), 404
    
    try:
        updated = story_engine.regenerate_frame_a(scene, str(project_dir))
        # Update in-place and save
        for i, s in enumerate(scenes):
            if s.get("number") == scene_number:
                scenes[i] = updated
                break
        with open(sp_path, "w") as f:
            json.dump(scene_prompts, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "ok", "scene": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/project/<project_id>/upload-frame/<int:scene_number>", methods=["POST"])
def api_upload_frame(project_id, scene_number):
    """Upload a custom Frame A image for a specific scene."""
    from werkzeug.utils import secure_filename as sec_fn
    
    project_dir = get_project_dir(project_id)
    sp_path = project_dir / "scene_prompts.json"
    if not sp_path.exists():
        return jsonify({"error": "Scene prompts not found"}), 404
    
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file provided"}), 400
    
    with open(sp_path) as fj:
        scene_prompts = json.load(fj)
    
    scenes = scene_prompts.get("scenes", [])
    scene_idx = next((i for i, s in enumerate(scenes) if s.get("number") == scene_number), None)
    if scene_idx is None:
        return jsonify({"error": f"Scene {scene_number} not found"}), 404
    
    frames_dir = project_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    
    ext = os.path.splitext(sec_fn(f.filename))[1] or ".png"
    filename = f"scene_{scene_number}_frame_a{ext}"
    filepath = frames_dir / filename
    f.save(filepath)
    
    scenes[scene_idx]["frame_a_filename"] = filename
    with open(sp_path, "w") as fj:
        json.dump(scene_prompts, fj, indent=2, ensure_ascii=False)
    
    return jsonify({"status": "uploaded", "filename": filename})


# =============================================================================
# ROUTES — Generation Steps
# =============================================================================

@app.route("/api/project/<project_id>/generate-breakdown", methods=["POST"])
def api_generate_breakdown(project_id):
    """Step 2: Analyze script and extract metadata + build narration."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    project_dir = get_project_dir(project_id)
    
    script_path = project_dir / "script.json"
    if not script_path.exists():
        return jsonify({"error": "Script not found. Upload a script first."}), 400
    
    with open(script_path) as f:
        script_data = json.load(f)
    
    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)
    
    def run():
        try:
            # Step 1: AI extracts metadata → story.json
            callback("🔍 Starting script breakdown...", "info")
            story = script_breakdown.extract_metadata(script_data, callback)
            
            with open(project_dir / "story.json", "w") as f:
                json.dump(story, f, indent=2, ensure_ascii=False)
            callback("💾 Story metadata saved", "info")
            
            # Step 2: Deterministic narration build → narration.json
            narration = script_breakdown.build_narration(script_data, callback)
            
            with open(project_dir / "narration.json", "w") as f:
                json.dump(narration, f, indent=2, ensure_ascii=False)
            callback("💾 Narration data saved", "info")
            
            # Update metadata
            meta["status"] = "breakdown_complete"
            if "breakdown" not in meta.get("steps_completed", []):
                meta.setdefault("steps_completed", []).append("breakdown")
            save_project_metadata(project_id, meta)
            
            callback("✅ Breakdown complete! Story metadata and narration ready.", "complete")
        except Exception as e:
            callback(f"❌ Breakdown failed: {str(e)}", "error")
    
    thread = threading.Thread(target=run)
    thread.start()
    
    return jsonify({"status": "generating", "message": "Breakdown started"})

@app.route("/api/project/<project_id>/generate-story", methods=["POST"])
def api_generate_story(project_id):
    """Step 1: Generate story from title (with quality gate + diversity)."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    title = meta["title"]
    duration = meta.get("duration_minutes", 20)
    episode_type = meta.get("episode_type", "build")
    
    # Check for A/B variant toggle from request body
    req_data = request.get_json(silent=True) or {}
    enable_variants = req_data.get("enable_variants", False)
    
    # Init SSE stream
    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)
    
    def run():
        try:
            story, quality_report = story_engine.generate_story(
                title, duration, episode_type, callback, 
                enable_variants=enable_variants
            )
            
            # Save story
            project_dir = get_project_dir(project_id)
            with open(project_dir / "story.json", "w") as f:
                json.dump(story, f, indent=2, ensure_ascii=False)
            
            # Save quality report
            if quality_report:
                with open(project_dir / "quality_report.json", "w") as f:
                    json.dump(quality_report, f, indent=2, ensure_ascii=False)
            
            # Update metadata
            meta["status"] = "story_generated"
            meta["story_strength"] = story.get("story_strength", 0)
            meta["quality_gate"] = quality_report.get("passed", False) if quality_report else None
            if "story" not in meta.get("steps_completed", []):
                meta.setdefault("steps_completed", []).append("story")
            save_project_metadata(project_id, meta)
            
            callback("✅ Story saved!", "complete")
        except Exception as e:
            callback(f"❌ Error: {str(e)}", "error")
    
    thread = threading.Thread(target=run)
    thread.start()
    
    return jsonify({"status": "generating", "message": "Story generation started"})



@app.route("/api/project/<project_id>/generate-elements", methods=["POST"])
def api_generate_elements(project_id):
    """Step 4: Analyze story for elements and generate reference images."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    project_dir = get_project_dir(project_id)
    
    story_path = project_dir / "story.json"
    narration_path = project_dir / "narration.json"
    if not story_path.exists():
        return jsonify({"error": "Story not found. Generate story first."}), 400
    if not narration_path.exists():
        return jsonify({"error": "Narration not found. Generate narration first."}), 400
    
    with open(story_path) as f:
        story = json.load(f)
    with open(narration_path) as f:
        narration = json.load(f)
    
    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)
    
    def run():
        try:
            # Step 1: Analyze elements needed
            elements_list = story_engine.analyze_elements(story, narration, callback)
            
            # Step 2: Generate reference images
            generated = story_engine.generate_elements(elements_list, str(project_dir), callback)
            
            # Save elements data
            with open(project_dir / "elements.json", "w") as f:
                json.dump(generated, f, indent=2, ensure_ascii=False)
            
            meta["status"] = "elements_generated"
            if "elements" not in meta.get("steps_completed", []):
                meta.setdefault("steps_completed", []).append("elements")
            save_project_metadata(project_id, meta)
            
            callback("\u2705 Elements generated and saved!", "complete")
        except Exception as e:
            callback(f"\u274c Error: {str(e)}", "error")
    
    thread = threading.Thread(target=run)
    thread.start()
    
    return jsonify({"status": "generating", "message": "Element generation started"})


@app.route("/api/project/<project_id>/regenerate-element/<element_id>", methods=["POST"])
def api_regenerate_element(project_id, element_id):
    """Regenerate the reference image for a single element."""
    project_dir = get_project_dir(project_id)
    elements_path = project_dir / "elements.json"
    
    if not elements_path.exists():
        return jsonify({"error": "Elements not found"}), 404
    
    with open(elements_path) as f:
        elements = json.load(f)
    
    # Find the element
    element = None
    element_idx = None
    for i, e in enumerate(elements):
        if e.get("element_id") == element_id:
            element = e
            element_idx = i
            break
    
    if element is None:
        return jsonify({"error": f"Element '{element_id}' not found"}), 404
    
    try:
        updated = story_engine.regenerate_single_element(element, str(project_dir))
        elements[element_idx] = updated
        
        with open(elements_path, "w") as f:
            json.dump(elements, f, indent=2, ensure_ascii=False)
        
        return jsonify({"status": "ok", "element": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/project/<project_id>/regenerate-element/<element_id>/edit", methods=["POST"])
def api_edit_element(project_id, element_id):
    """Edit an element's image prompt via AI and regenerate."""
    data = request.get_json()
    feedback = data.get("feedback")
    if not feedback:
        return jsonify({"error": "No feedback provided"}), 400
        
    project_dir = get_project_dir(project_id)
    elements_path = project_dir / "elements.json"
    
    if not elements_path.exists():
        return jsonify({"error": "Elements not found"}), 404
        
    with open(elements_path) as f:
        elements = json.load(f)
        
    # Find the element
    element = None
    element_idx = None
    for i, e in enumerate(elements):
        if e.get("element_id") == element_id:
            element = e
            element_idx = i
            break
            
    if element is None:
        return jsonify({"error": f"Element '{element_id}' not found"}), 404
        
    try:
        updated = story_engine.edit_element_with_ai(element, feedback, str(project_dir))
        elements[element_idx] = updated
        
        with open(elements_path, "w") as f:
            json.dump(elements, f, indent=2, ensure_ascii=False)
            
        return jsonify({"status": "ok", "element": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/project/<project_id>/upload-element/<element_id>", methods=["POST"])
def api_upload_element(project_id, element_id):
    """Upload a custom image for a single element."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    
    project_dir = get_project_dir(project_id)
    elements_path = project_dir / "elements.json"
    
    if not elements_path.exists():
        return jsonify({"error": "Elements not found"}), 404
    
    with open(elements_path) as f_json:
        elements = json.load(f_json)
    
    # Find the element
    element_idx = None
    for i, e in enumerate(elements):
        if e.get("element_id") == element_id:
            element_idx = i
            break
    
    if element_idx is None:
        return jsonify({"error": f"Element '{element_id}' not found"}), 404
    
    # Save file as {element_id}.{ext}
    from werkzeug.utils import secure_filename
    ext = os.path.splitext(secure_filename(f.filename))[1] or ".png"
    filename = f"{element_id}{ext}"
    
    elements_dir = project_dir / "elements"
    elements_dir.mkdir(parents=True, exist_ok=True)
    
    # Remove old image if exists (could be different extension)
    for old_file in elements_dir.glob(f"{element_id}.*"):
        old_file.unlink()
    
    filepath = elements_dir / filename
    f.save(filepath)
    
    # Update elements.json
    elements[element_idx]["image_filename"] = filename
    with open(elements_path, "w") as f_json:
        json.dump(elements, f_json, indent=2, ensure_ascii=False)
    
    return jsonify({"status": "uploaded", "filename": filename})


@app.route("/api/project/<project_id>/generate-scene-prompts", methods=["POST"])
def api_generate_scene_prompts(project_id):
    """Step 5 (LEGACY): Generate unified scene prompts from narration + elements."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    project_dir = get_project_dir(project_id)
    
    story_path = project_dir / "story.json"
    narration_path = project_dir / "narration.json"
    elements_path = project_dir / "elements.json"
    
    if not story_path.exists():
        return jsonify({"error": "Story not found."}), 400
    if not narration_path.exists():
        return jsonify({"error": "Narration not found."}), 400
    if not elements_path.exists():
        return jsonify({"error": "Elements not found. Generate elements first."}), 400
    
    with open(story_path) as f:
        story = json.load(f)
    with open(narration_path) as f:
        narration = json.load(f)
    with open(elements_path) as f:
        elements = json.load(f)
    
    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)
    
    def run():
        try:
            scene_prompts = story_engine.generate_scene_prompts(
                story, narration, elements, progress_callback=callback
            )
            
            # Generate Frame A images for each scene
            callback("🖼️ Starting Frame A image generation...", "info")
            story_engine.generate_frame_a_images(
                scene_prompts["scenes"], str(project_dir), progress_callback=callback
            )
            
            with open(project_dir / "scene_prompts.json", "w") as f:
                json.dump(scene_prompts, f, indent=2, ensure_ascii=False)
            
            meta["status"] = "scene_prompts_generated"
            if "scene_prompts" not in meta.get("steps_completed", []):
                meta.setdefault("steps_completed", []).append("scene_prompts")
            save_project_metadata(project_id, meta)
            
            callback("\u2705 Scene prompts + Frame A images saved!", "complete")
        except Exception as e:
            callback(f"\u274c Error: {str(e)}", "error")
    
    thread = threading.Thread(target=run)
    thread.start()
    
    return jsonify({"status": "generating", "message": "Scene prompt generation started"})


# =============================================================================
# ROUTES — Chapter Production Pipeline (NEW)
# =============================================================================


@app.route("/api/project/<project_id>/storyboard/intro", methods=["GET"])
def api_get_intro_storyboard(project_id):
    """Get the intro storyboard data."""
    project_dir = get_project_dir(project_id)
    storyboard_path = project_dir / "production" / "intro" / "storyboard.json"
    if not storyboard_path.exists():
        return jsonify({"error": "Intro storyboard not generated yet"}), 404
    with open(storyboard_path) as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/project/<project_id>/storyboard/<block_folder>", methods=["GET"])
def api_get_block_storyboard(project_id, block_folder):
    """Get the storyboard data for an arbitrary block (like break_1 or close)."""
    project_dir = get_project_dir(project_id)
    
    # Check if this is a legacy chapter index request (e.g. "1" instead of "chapter_1")
    if block_folder.isdigit():
        block_folder = f"chapter_{int(block_folder) + 1}"
        
    storyboard_path = project_dir / "production" / block_folder / "storyboard.json"
    if not storyboard_path.exists():
        return jsonify({"error": f"{block_folder} storyboard not generated yet"}), 404
    with open(storyboard_path) as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/project/<project_id>/scene-image/<block_folder>/<filename>")
def api_scene_image(project_id, block_folder, filename):
    """Serve a generated scene image."""
    project_dir = get_project_dir(project_id)
    img_path = project_dir / "production" / block_folder / "images" / filename
    if not img_path.exists():
        return "", 404
    resp = send_file(str(img_path))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@app.route("/api/project/<project_id>/edit-scene", methods=["POST"])
def api_edit_scene(project_id):
    """Edit a single scene via Gemini instruction, then regenerate its image."""
    data = request.get_json()
    block_folder = data.get("block_folder", "intro")
    scene_index = data.get("scene_index", 0)
    instruction = data.get("instruction", "")

    if not instruction:
        return jsonify({"error": "No instruction provided"}), 400

    project_dir = get_project_dir(project_id)
    storyboard_path = project_dir / "production" / block_folder / "storyboard.json"

    if not storyboard_path.exists():
        return jsonify({"error": "Storyboard not found"}), 404

    # Setup SSE progress
    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)

    def edit_worker():
        try:
            with open(storyboard_path) as f:
                sb_data = json.load(f)

            scenes = sb_data.get("storyboard", [])
            if scene_index >= len(scenes):
                callback("❌ Scene index out of range", "error")
                return

            scene = scenes[scene_index]
            scene_num = scene.get("scene_number", scene_index + 1)
            callback(f"✏️ Editing Scene {scene_num}...", "info")

            # Ask Gemini to modify the scene
            edit_prompt = f"""You are editing a scene in a video storyboard. Here is the current scene JSON:

{json.dumps(scene, indent=2, ensure_ascii=False)}

USER INSTRUCTION: {instruction}

Apply the user's instruction to modify this scene. Return ONLY the updated JSON object with the same structure (scene_number, type, duration, visual_description, camera, narration, elements, etc.). Keep fields the user didn't mention. Return valid JSON only, no markdown."""

            client = story_engine.init_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[edit_prompt]
            )

            raw = response.text.strip()
            # Clean markdown wrapping
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
            raw = raw.strip()

            updated_scene = json.loads(raw)
            callback(f"✅ Scene {scene_num} updated by AI", "info")

            # Preserve scene_number and scene_image (will regenerate)
            updated_scene["scene_number"] = scene_num

            # Replace scene in storyboard
            scenes[scene_index] = updated_scene

            # Regenerate image
            vis_desc = updated_scene.get("visual_description", "")
            if vis_desc:
                callback(f"🖼️ Regenerating image for Scene {scene_num}...", "info")

                images_dir = project_dir / "production" / block_folder / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                img_filename = f"scene_{scene_num:02d}.png"
                img_path = images_dir / img_filename

                img_config = {"image_generation": {"aspect_ratio": "16:9"}}
                img_prompt = f"Cinematic 16:9 film still. {vis_desc} Photorealistic, dramatic lighting, nature documentary style."

                # Character reference
                elements_dir = project_dir / "elements"
                show_settings = json.loads((Path("config/show_settings.json")).read_text())
                presenter_img = Path("config/presenter") / show_settings.get("presenter", {}).get("turnaround_image", "")

                ref_path = None
                scene_type = updated_scene.get("type", "bridge")
                scene_elements = updated_scene.get("elements", [])

                if scene_type == "presenter" and presenter_img.exists():
                    ref_path = str(presenter_img)
                elif scene_elements:
                    for elem_name in scene_elements:
                        elem_file = elem_name.lower().replace(" ", "_").replace("'", "").replace("(", "").replace(")", "") + ".png"
                        elem_path = elements_dir / elem_file
                        if elem_path.exists():
                            ref_path = str(elem_path)
                            break

                try:
                    if ref_path:
                        story_engine.generate_image_with_ref(img_prompt, str(img_path), ref_path, config=img_config)
                    else:
                        story_engine.generate_image(img_prompt, str(img_path), config=img_config)
                    updated_scene["scene_image"] = img_filename
                    callback(f"✅ Image regenerated for Scene {scene_num}", "info")
                except Exception as img_err:
                    callback(f"⚠️ Image regeneration failed: {str(img_err)[:100]}", "error")
                    updated_scene["scene_image"] = scene.get("scene_image")

            # Save updated storyboard
            scenes[scene_index] = updated_scene
            sb_data["storyboard"] = scenes
            with open(storyboard_path, "w") as f:
                json.dump(sb_data, f, indent=2, ensure_ascii=False)

            callback(f"✅ Scene {scene_num} saved!", "complete")

        except json.JSONDecodeError as e:
            callback(f"❌ Failed to parse AI response: {str(e)}", "error")
        except Exception as e:
            callback(f"❌ Edit failed: {str(e)[:200]}", "error")

    threading.Thread(target=edit_worker, daemon=True).start()
    return jsonify({"status": "editing", "message": f"Editing scene {scene_index + 1}..."})


@app.route("/api/project/<project_id>/update-scene", methods=["POST"])
def api_update_scene(project_id):
    """Update scene from action text, AI-generate visual_description, optionally regenerate image."""
    data = request.get_json()
    block_folder = data.get("block_folder", "intro")
    scene_index = data.get("scene_index", 0)
    scene_type = data.get("scene_type", "bridge")
    action = data.get("action", "")
    narration = data.get("narration", "")
    duration = data.get("duration", "8s")
    regen_image = data.get("regenerate_image", True)

    if not action:
        return jsonify({"error": "Action is required"}), 400

    project_dir = get_project_dir(project_id)
    storyboard_path = project_dir / "production" / block_folder / "storyboard.json"

    if not storyboard_path.exists():
        return jsonify({"error": "Storyboard not found"}), 404

    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)

    def update_worker():
        try:
            with open(storyboard_path) as f:
                sb_data = json.load(f)

            scenes = sb_data.get("storyboard", [])
            if scene_index >= len(scenes):
                callback("❌ Scene index out of range", "error")
                return

            scene = scenes[scene_index]
            scene_num = scene.get("scene_number", scene_index + 1)

            # Generate visual_description from action via Gemini
            callback(f"🤖 Generating visual description from action...", "info")
            gen_prompt = f"""You are a storyboard visual director for a nature documentary show called "The Last Shelter".
Given this scene info, generate a detailed cinematic visual description for image generation AND a camera instruction.

Scene type: {scene_type.upper()}
Action: {action}
Narration: {narration or '(none)'}

Respond in this exact format (nothing else):
VISUAL: [detailed visual description for 16:9 cinematic image IN SPANISH, 2-3 sentences, photorealistic, include lighting, mood, specific details]
CAMERA: [camera angle and movement, e.g. "plano medio, ligero push-in, a la altura de ojos"]"""

            try:
                gen_result = story_engine.generate_text(gen_prompt)
                visual_desc = ""
                camera = ""
                for line in gen_result.strip().split("\n"):
                    if line.startswith("VISUAL:"):
                        visual_desc = line[7:].strip()
                    elif line.startswith("CAMERA:"):
                        camera = line[7:].strip()
                if not visual_desc:
                    visual_desc = action  # fallback
                callback(f"✅ Visual description generated", "info")
            except Exception as gen_err:
                visual_desc = action
                camera = ""
                callback(f"⚠️ AI generation failed, using action as visual: {str(gen_err)[:80]}", "info")

            # Update fields
            scene["type"] = scene_type
            scene["action"] = action
            scene["visual_description"] = visual_desc
            scene["camera"] = camera
            scene["narration"] = narration
            scene["duration"] = duration
            callback(f"✅ Scene {scene_num} fields updated", "info")

            # Regenerate image if requested
            if regen_image:
                callback(f"🖼️ Generating image for Scene {scene_num}...", "info")

                images_dir = project_dir / "production" / block_folder / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                img_filename = f"scene_{scene_num:02d}.png"
                img_path = images_dir / img_filename
                img_config = {"image_generation": {"aspect_ratio": "16:9"}}
                img_prompt = f"Cinematic 16:9 film still. {visual_desc} Photorealistic, dramatic lighting, nature documentary style."

                # Character reference
                try:
                    show_settings = json.loads((Path("config/show_settings.json")).read_text())
                    presenter_img = Path("config/presenter") / show_settings.get("presenter", {}).get("turnaround_image", "")
                except Exception:
                    presenter_img = Path("")

                ref_path = None
                if scene_type == "presenter" and presenter_img.exists():
                    ref_path = str(presenter_img)

                try:
                    if ref_path:
                        story_engine.generate_image_with_ref(img_prompt, str(img_path), ref_path, config=img_config)
                    else:
                        story_engine.generate_image(img_prompt, str(img_path), config=img_config)
                    scene["scene_image"] = img_filename
                    callback(f"✅ Image regenerated for Scene {scene_num}", "info")
                except Exception as img_err:
                    callback(f"⚠️ Image failed: {str(img_err)[:100]}", "error")

            # Save
            sb_data["storyboard"] = scenes
            with open(storyboard_path, "w") as f:
                json.dump(sb_data, f, indent=2, ensure_ascii=False)

            callback(f"✅ Scene {scene_num} saved!", "complete")

        except Exception as e:
            callback(f"❌ Update failed: {str(e)[:200]}", "error")

    threading.Thread(target=update_worker, daemon=True).start()
    return jsonify({"status": "updating", "message": f"Updating scene {scene_index + 1}..."})


@app.route("/api/project/<project_id>/generate-prompts", methods=["POST"])
def api_generate_prompts(project_id):
    """Generate Kling video prompts for all scenes in a block using Gemini."""
    data = request.get_json()
    block_folder = data.get("block_folder", "intro")

    project_dir = get_project_dir(project_id)
    storyboard_path = project_dir / "production" / block_folder / "storyboard.json"

    if not storyboard_path.exists():
        return jsonify({"error": "Storyboard not found"}), 404

    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)

    def prompts_worker():
        try:
            with open(storyboard_path) as f:
                sb_data = json.load(f)

            scenes = sb_data.get("storyboard", [])
            if not scenes:
                callback("❌ No scenes to generate prompts for", "error")
                return

            # Load show settings for character refs
            try:
                show_settings = json.loads(Path("config/show_settings.json").read_text())
                presenter_name = show_settings.get("presenter", {}).get("name", "Jack Harlan")
            except Exception:
                presenter_name = "Jack Harlan"

            # Load ALL elements from elements.json
            elements_path = project_dir / "elements.json"
            available_elements = []
            element_map = {}  # Map from original label -> simplified prompt name
            
            # Helper to format element labels into safe PascalCase without spaces or apostrophes
            def sanitize_element_name(name):
                return name.replace("'", "").replace(" ", "").replace("(", "").replace(")", "").title().replace(" ", "")

            if elements_path.exists():
                try:
                    with open(elements_path) as ef:
                        elements_list = json.load(ef)
                    for el in elements_list:
                        label = el.get("label", el.get("element_id", ""))
                        if "prompt_name" in el and el.get("prompt_name"):
                            pname = el["prompt_name"].replace(" ", "").replace("'", "")
                        else:
                            pname = sanitize_element_name(label)
                        
                        element_map[label] = pname
                        # Also map by id just in case
                        element_map[el.get("element_id")] = pname
                        
                        if pname not in available_elements:
                            available_elements.append(pname)
                except Exception as e:
                    pass

            # Load story context for location image generation
            story_path = project_dir / "story.json"
            story_context_loc = ""
            if story_path.exists():
                with open(story_path) as sf:
                    story_data = json.load(sf)
                loc = story_data.get("location", {})
                timeline = story_data.get("timeline", {})
                loc_name = loc.get("name", "remote wilderness")
                terrain = loc.get("terrain", "wilderness")
                climate = loc.get("climate", "")
                season = timeline.get("season", "")
                story_context_loc = f"{loc_name}, {terrain}"
                if climate:
                    story_context_loc += f". {climate}"
                if season:
                    story_context_loc += f". Season: {season}"
            else:
                story_data = {}

            # Build scene summary for Gemini
            callback(f"🤖 Generating Kling prompts for {len(scenes)} scenes...", "info")

            scene_descriptions = []
            for s in scenes:
                # Sanitize the element list from the scene using the element map
                safe_scene_elements = [element_map.get(e, sanitize_element_name(e)) for e in s.get("elements", [])]
                scene_descriptions.append(
                    f"SCENE {s['scene_number']} | {s.get('type','bridge').upper()} | {s.get('duration','8s')}\n"
                    f"Action: {s.get('action','')}\n"
                    f"Narration: {s.get('narration','(none)')}\n"
                    f"Visual: {s.get('visual_description','')}\n"
                    f"Elements: {', '.join(safe_scene_elements)}"
                )

            # Load reference prompts for few-shot examples
            ref_prompts_text = ""
            ref_path = Path("docs/VIDEO_PROMPT_EXAMPLES.md")
            if ref_path.exists():
                ref_prompts_text = ref_path.read_text()
                callback("📚 Loaded reference prompts for quality matching", "info")
            else:
                callback("⚠️ No reference prompts found — generating without examples", "info")

            batch_prompt = f"""You are an expert cinematic video prompt writer for "The Last Shelter", a high-end nature survival documentary series.
Your job is to generate ULTRA-DETAILED Kling 3.0 multishot video prompts for each scene.

AVAILABLE ELEMENTS (use @ prefix in the prompt text for ALL elements — characters, vehicles, objects):
- @Jack (presenter: {presenter_name})
{chr(10).join(f'- @{e}' for e in available_elements if e.lower() != presenter_name.lower())}

CRITICAL QUALITY RULES:
1. ALWAYS start with "No music."
2. Use @CharacterName when a character appears (e.g. @Jack, @Erik)
3. EVERY scene MUST be highly cinematic. Use multiple "Cut to" angles, tracking shots, close-ups, and sweeping wides. NEVER generate a short, simple, or static scene description.
4. Write DENSE, HYPER-SPECIFIC visual paragraphs: detail body mechanics, dirt, sweat, texturing of clothes, lighting behavior (dappled light, rim lighting), weather interaction (snow blowing off a roof, breath misting), and camera movement (hand-held tracking, low-angle drone). The prompt text should be long and exhaustively detailed.
5. For PRESENTER scenes (intro/outro) with dialogue, include the EXACT narration split across the multishot cuts: @Jack speaks to camera: "exact text"
6. For all other NON-PRESENTER scenes (flashback, anticipatorio, bridge, chapter action), DO NOT include any dialogue, speech, or "Voice-over narration" in the video prompt text. Voice-overs are added in post-production. Focus 100% on pure cinematic visual action.
7. ALWAYS end the prompt with lighting/color palette description + "4K."
8. ALWAYS include a separate SFX line with detailed, layered sound design.
9. Each prompt needs a LOCATION_ID (reusable name, snake_case). Scenes sharing same physical location share the same LOCATION_ID.
10. Write a one-line LOCATION_PROMPT for generating the empty location image (no people, 16:9).

HERE ARE ALL THE REFERENCE PROMPTS — STUDY THEM CAREFULLY AND MATCH THIS EXACT LEVEL OF CINEMATIC DETAIL, MULTISHOT STRUCTURE, AND ATMOSPHERIC RICHNESS:

{ref_prompts_text}

IMPORTANT: The above are EXAMPLES of the quality standard. Now generate NEW prompts for the following scenes with the SAME level of detail, creativity, and cinematic direction:

{chr(10).join(scene_descriptions)}

IMAGE REFERENCES — CRITICAL:
- Each scene will have a scene image (the character/action shot) and optionally a location image (the background environment)
- When only ONE image exists (the location), use @Image
- When TWO or more images exist, number them: @Image1 is the scene image (character shot), @Image2 is the location (background)
- Example of ONE image: "@Image The camera slowly tracks across the snow-covered clearing..."
- Example of TWO images: "@Image1 @Erik walks through @Image2, a snow-covered clearing..."

ELEMENT USAGE — CRITICAL:
- Use @ElementName for ALL elements.
- The @ElementName MUST match the available elements exactly: {', '.join(f'@{e}' for e in available_elements if e.lower() != presenter_name.lower())}
- Do NOT use spaces, possessives, or descriptive names not in the list. For example, use @Pickup instead of @EriksPickupTruck or @Erik's Pickup Truck.
- If a vehicle, tent, tool, or object is an available element, ALWAYS use the @ reference.

RESPOND in this EXACT format for each scene (nothing else):

===SCENE N===
PROMPT: [ultra-detailed cinematic Kling multishot prompt matching the reference quality, using @Image or @Image1/@Image2 references]
SFX: [detailed, layered sound effects]
ELEMENTS: [comma-separated list of ALL elements used — characters, vehicles, objects — WITHOUT @, or "none"]
LOCATIONS: [pipe-separated list of location entries. Each entry: location_id | one-line image prompt. Example below]

Example with ONE location:
LOCATIONS: helicopter_interior | Interior of a helicopter cabin with snowy landscape visible through the window

Example with TWO locations (when prompt uses Cut to different location):
LOCATIONS: helicopter_interior | Interior of a helicopter cabin | forest_clearing_autumn | A sun-dappled clearing in a boreal forest during golden autumn

IMPORTANT: Use @Image, @Image1, @Image2 etc. in the PROMPT text to reference which location image applies to which part of the multishot.
===END==="""

            try:
                gen_result = story_engine.generate_text(batch_prompt, max_tokens=30000)
                callback("✅ Prompts generated by AI", "info")
            except Exception as gen_err:
                callback(f"❌ AI generation failed: {str(gen_err)[:150]}", "error")
                return

            # Parse the result
            import re
            scene_blocks = re.split(r'===SCENE\s+(\d+)===', gen_result)

            prompts_by_scene = {}
            i = 1
            while i < len(scene_blocks) - 1:
                scene_num = int(scene_blocks[i])
                content = scene_blocks[i + 1].split("===END===")[0].strip()

                prompt_text = ""
                sfx = ""
                elements = []
                locations = []

                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("PROMPT:"):
                        prompt_text = line[7:].strip()
                        continue
                    elif line.startswith("SFX:"):
                        sfx = line[4:].strip()
                    elif line.startswith("ELEMENTS:"):
                        raw = line[9:].strip()
                        if raw.lower() != "none":
                            elements = [e.strip().replace("@", "") for e in raw.split(",") if e.strip()]
                    elif line.startswith("LOCATIONS:"):
                        raw = line[10:].strip()
                        # Parse pipe-separated: loc_id1 | prompt1 | loc_id2 | prompt2
                        parts = [p.strip() for p in raw.split("|")]
                        j = 0
                        while j < len(parts) - 1:
                            loc_id = parts[j].strip()
                            loc_prompt = parts[j + 1].strip()
                            if loc_id and loc_prompt:
                                locations.append({
                                    "id": loc_id,
                                    "prompt": loc_prompt,
                                    "image": None
                                })
                            j += 2
                    # Legacy single-location format support
                    elif line.startswith("LOCATION_ID:"):
                        loc_id = line[12:].strip()
                        if locations:
                            locations[0]["id"] = loc_id
                        else:
                            locations.append({"id": loc_id, "prompt": "", "image": None})
                    elif line.startswith("LOCATION_PROMPT:"):
                        loc_prompt = line[16:].strip()
                        if locations:
                            locations[-1]["prompt"] = loc_prompt
                        else:
                            locations.append({"id": "", "prompt": loc_prompt, "image": None})
                    elif prompt_text and not any(line.startswith(p) for p in ["SFX:", "ELEMENTS:", "LOCATIONS:", "LOCATION_ID:", "LOCATION_PROMPT:"]):
                        prompt_text += " " + line

                prompts_by_scene[scene_num] = {
                    "prompt_text": prompt_text.strip(),
                    "sfx": sfx,
                    "elements": elements,
                    "locations": locations
                }
                i += 2

            callback(f"📝 Parsed {len(prompts_by_scene)} prompts", "info")

            # ─── POST-PROCESSING: auto-fix elements and narration ───
            for s in scenes:
                snum = s.get("scene_number")
                if snum not in prompts_by_scene:
                    continue
                pd = prompts_by_scene[snum]
                pt = pd.get("prompt_text", "")
                stype = s.get("type", "").lower()
                narr = s.get("narration", "")

                # Fix 1: If @PresenterName appears in prompt text, add presenter to elements
                if presenter_name and f"@{presenter_name.split()[0]}" in pt:
                    if presenter_name not in pd["elements"]:
                        pd["elements"].append(presenter_name)

                # Removed the forceful voice-over addition logic for non-presenter scenes.
                # All narration for those scenes is handled strictly in post-production audio editing.

                # Fix 3: Sync scene elements to prompt elements
                for el in s.get("elements", []):
                    safe_el = element_map.get(el, sanitize_element_name(el))
                    if safe_el not in pd["elements"]:
                        pd["elements"].append(safe_el)

            callback(f"🔧 Post-processed {len(prompts_by_scene)} prompts (elements & narration sync)", "info")

            # Generate location images (deduplicate by location_id)
            images_dir = project_dir / "production" / block_folder / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            img_config = {"image_generation": {"aspect_ratio": "16:9"}}

            generated_locations = {}  # location_id -> filename

            for scene_num, prompt_data in sorted(prompts_by_scene.items()):
                for loc in prompt_data.get("locations", []):
                    loc_id = loc.get("id", "")
                    if not loc_id:
                        continue

                    if loc_id in generated_locations:
                        loc["image"] = generated_locations[loc_id]
                        callback(f"♻️ Scene {scene_num}: reusing location '{loc_id}'", "info")
                        continue

                    loc_filename = f"loc_{loc_id}.png"
                    loc_path = images_dir / loc_filename

                    # Skip if image already exists
                    if loc_path.exists():
                        generated_locations[loc_id] = loc_filename
                        loc["image"] = loc_filename
                        callback(f"♻️ Scene {scene_num}: location '{loc_id}' already exists", "info")
                        continue

                    loc_prompt_text = loc.get("prompt", "")
                    if not loc_prompt_text:
                        loc_prompt_text = f"Empty environment, {loc_id.replace('_', ' ')}, no people, cinematic lighting"

                    img_prompt = f"Real photography, Canon EOS R5. Setting: {story_context_loc}. {loc_prompt_text} NO people in frame. 16:9 landscape format. Photorealistic, NOT CGI."

                    callback(f"🖼️ Scene {scene_num}: generating location '{loc_id}'...", "info")
                    try:
                        story_engine.generate_image(img_prompt, str(loc_path), config=img_config)
                        generated_locations[loc_id] = loc_filename
                        loc["image"] = loc_filename
                        callback(f"✅ Location '{loc_id}' generated", "info")
                    except Exception as img_err:
                        callback(f"⚠️ Location image failed for '{loc_id}': {str(img_err)[:80]}", "info")

            # Save prompts into storyboard.json scenes
            for scene in scenes:
                sn = scene["scene_number"]
                if sn in prompts_by_scene:
                    scene["prompt"] = prompts_by_scene[sn]

            sb_data["storyboard"] = scenes
            with open(storyboard_path, "w") as f:
                json.dump(sb_data, f, indent=2, ensure_ascii=False)

            callback(f"✅ All prompts saved! ({len(prompts_by_scene)} prompts, {len(generated_locations)} unique locations)", "complete")

        except Exception as e:
            callback(f"❌ Prompt generation failed: {str(e)[:200]}", "error")

    threading.Thread(target=prompts_worker, daemon=True).start()
    return jsonify({"status": "generating", "message": f"Generating prompts for {block_folder}..."})


@app.route("/api/project/<project_id>/edit-prompt", methods=["POST"])
def api_edit_prompt(project_id):
    """Rewrite a prompt based on user feedback using AI."""
    data = request.get_json()
    block_folder = data.get("block_folder", "intro")
    scene_index = data.get("scene_index", 0)
    current_prompt = data.get("current_prompt", "")
    current_sfx = data.get("current_sfx", "")
    feedback = data.get("feedback", "")

    if not feedback.strip():
        return jsonify({"error": "No feedback provided"}), 400

    project_dir = Path(f"projects/{project_id}")
    storyboard_path = project_dir / "production" / block_folder / "storyboard.json"

    if not storyboard_path.exists():
        return jsonify({"error": "Storyboard not found"}), 404

    # Load reference prompts for quality context
    ref_prompts_text = ""
    ref_path = Path("docs/VIDEO_PROMPT_EXAMPLES.md")
    if ref_path.exists():
        ref_prompts_text = ref_path.read_text()

    # Build the edit prompt for Gemini
    edit_prompt = f"""You are an expert cinematic video prompt writer for "The Last Shelter", a high-end nature survival documentary.

HERE ARE REFERENCE PROMPTS showing the quality standard:
{ref_prompts_text}

CURRENT PROMPT:
{current_prompt}
SFX: {current_sfx}

USER FEEDBACK:
{feedback}

INSTRUCTIONS:
1. Rewrite the prompt incorporating the user's feedback
2. Keep the same quality level as the reference prompts
3. Maintain "No music." at the start
4. Keep multishot "Cut to" structure for presenter scenes
5. Keep the lighting/color palette + "4K." at the end
6. Return ONLY the rewritten prompt and SFX, nothing else

RESPOND in this EXACT format:
PROMPT: [rewritten prompt]
SFX: [updated sound effects]"""

    try:
        gen_result = story_engine.generate_text(edit_prompt, max_tokens=4000)
        if not gen_result:
            return jsonify({"error": "AI returned empty response. Try again."}), 500

        # Parse result
        new_prompt = current_prompt
        new_sfx = current_sfx
        for line in gen_result.strip().split("\n"):
            if line.startswith("PROMPT:"):
                new_prompt = line[7:].strip()
            elif line.startswith("SFX:"):
                new_sfx = line[4:].strip()

        # Handle multiline PROMPT (everything after PROMPT: until SFX:)
        if "PROMPT:" in gen_result and "SFX:" in gen_result:
            prompt_part = gen_result.split("PROMPT:", 1)[1]
            prompt_part = prompt_part.split("SFX:", 1)[0].strip()
            sfx_part = gen_result.split("SFX:", 1)[1].strip()
            if prompt_part:
                new_prompt = prompt_part
            if sfx_part:
                new_sfx = sfx_part

        # Save to storyboard.json
        with open(storyboard_path) as f:
            sb_data = json.load(f)

        scenes = sb_data.get("storyboard", [])
        if scene_index < len(scenes):
            if "prompt" not in scenes[scene_index]:
                scenes[scene_index]["prompt"] = {}
            scenes[scene_index]["prompt"]["prompt_text"] = new_prompt
            scenes[scene_index]["prompt"]["sfx"] = new_sfx

            with open(storyboard_path, "w") as f:
                json.dump(sb_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            "status": "ok",
            "prompt_text": new_prompt,
            "sfx": new_sfx
        })

    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/api/project/<project_id>/edit-location-image", methods=["POST"])
def api_edit_location_image(project_id):
    """Regenerate a location image based on user feedback. Updates all scenes sharing the same location_id."""
    data = request.get_json()
    block_folder = data.get("block_folder", "intro")
    location_id = data.get("location_id", "")
    location_image = data.get("location_image", "")
    current_prompt = data.get("current_prompt", "")
    feedback = data.get("feedback", "")
    reference_image = data.get("reference_image", "")  # optional: filename of image to use as visual reference

    if not feedback.strip():
        return jsonify({"error": "No feedback provided"}), 400
    if not location_id:
        return jsonify({"error": "No location_id provided"}), 400

    project_dir = Path(f"projects/{project_id}")
    block_dir = project_dir / "production" / block_folder
    storyboard_path = block_dir / "storyboard.json"

    if not storyboard_path.exists():
        return jsonify({"error": "Storyboard not found"}), 404


    try:
        # Build new image prompt directly: base description + user modifications
        new_loc_prompt = f"{current_prompt}. Changes: {feedback}"

        # Generate the new image
        img_config = {"aspect_ratio": "16:9"}
        img_prompt = f"Real photography, Canon EOS R5. {new_loc_prompt} NO people in frame. 16:9 landscape format. Photorealistic, NOT CGI."
        images_dir = block_dir / "images"
        images_dir.mkdir(exist_ok=True)
        loc_path = images_dir / location_image

        if reference_image:
            # Use reference image for visual consistency (image-to-image)
            ref_path = images_dir / reference_image
            if ref_path.exists():
                story_engine.generate_image_with_ref(img_prompt, str(loc_path), str(ref_path), config=img_config)
            else:
                story_engine.generate_image(img_prompt, str(loc_path), config=img_config)
        else:
            story_engine.generate_image(img_prompt, str(loc_path), config=img_config)

        # Update location_prompt in ALL scenes sharing this location_id
        with open(storyboard_path) as f:
            sb_data = json.load(f)

        updated_count = 0
        for scene in sb_data.get("storyboard", []):
            p = scene.get("prompt", {})
            # Update new locations array
            for loc in p.get("locations", []):
                if loc.get("id") == location_id:
                    loc["prompt"] = new_loc_prompt
                    updated_count += 1
            # Also update legacy fields
            if p.get("location_id") == location_id:
                p["location_prompt"] = new_loc_prompt
                if not p.get("locations"):
                    updated_count += 1

        with open(storyboard_path, "w") as f:
            json.dump(sb_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            "status": "ok",
            "new_prompt": new_loc_prompt,
            "location_image": location_image,
            "updated_scenes": updated_count
        })

    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/api/project/<project_id>/insert-scene", methods=["POST"])
def api_insert_scene(project_id):
    """Insert a new scene at a given position, renumber, generate image, save."""
    data = request.get_json()
    block_folder = data.get("block_folder", "intro")
    insert_index = data.get("insert_index", 0)
    scene_type = data.get("scene_type", "bridge")
    action = data.get("action", "")
    narration = data.get("narration", "")
    duration = data.get("duration", "8s")

    if not action:
        return jsonify({"error": "Action is required"}), 400

    project_dir = get_project_dir(project_id)
    storyboard_path = project_dir / "production" / block_folder / "storyboard.json"

    if not storyboard_path.exists():
        return jsonify({"error": "Storyboard not found"}), 404

    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)

    def insert_worker():
        try:
            with open(storyboard_path) as f:
                sb_data = json.load(f)

            scenes = sb_data.get("storyboard", [])
            images_dir = project_dir / "production" / block_folder / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            # Renumber images for scenes AFTER the insert point (reverse order to avoid conflicts)
            callback(f"🔢 Renumbering scenes after position {insert_index + 1}...", "info")
            for i in range(len(scenes) - 1, insert_index - 1, -1):
                old_num = scenes[i].get("scene_number", i + 1)
                new_num = old_num + 1
                scenes[i]["scene_number"] = new_num

                # Rename image file
                old_img = scenes[i].get("scene_image", "")
                if old_img:
                    new_img = f"scene_{new_num:02d}.png"
                    old_path = images_dir / old_img
                    new_path = images_dir / new_img
                    if old_path.exists():
                        import shutil
                        shutil.move(str(old_path), str(new_path))
                    scenes[i]["scene_image"] = new_img

            # Generate visual_description from action via Gemini
            callback(f"🤖 Generating visual description from action...", "info")
            gen_prompt = f"""You are a storyboard visual director for a nature documentary show called "The Last Shelter".
Given this scene info, generate a detailed cinematic visual description for image generation AND a camera instruction.

Scene type: {scene_type.upper()}
Action: {action}
Narration: {narration or '(none)'}

Respond in this exact format (nothing else):
VISUAL: [detailed visual description for 16:9 cinematic image IN SPANISH, 2-3 sentences, photorealistic, include lighting, mood, specific details]
CAMERA: [camera angle and movement, e.g. "plano medio, ligero push-in, a la altura de ojos"]"""

            try:
                gen_result = story_engine.generate_text(gen_prompt)
                visual_desc = ""
                camera = ""
                for line in gen_result.strip().split("\n"):
                    if line.startswith("VISUAL:"):
                        visual_desc = line[7:].strip()
                    elif line.startswith("CAMERA:"):
                        camera = line[7:].strip()
                if not visual_desc:
                    visual_desc = action
                callback(f"✅ Visual description generated", "info")
            except Exception as gen_err:
                visual_desc = action
                camera = ""
                callback(f"⚠️ AI generation failed, using action as visual: {str(gen_err)[:80]}", "info")

            # Create the new scene
            new_scene_num = insert_index + 1
            new_scene = {
                "scene_number": new_scene_num,
                "type": scene_type,
                "duration": duration,
                "narration": narration,
                "action": action,
                "visual_description": visual_desc,
                "camera": camera,
                "elements": [],
                "sfx": "",
                "scene_image": None
            }

            scenes.insert(insert_index, new_scene)
            callback(f"✅ Scene {new_scene_num} ({scene_type.upper()}) inserted", "info")

            # Generate image
            callback(f"🖼️ Generating image for Scene {new_scene_num}...", "info")
            img_filename = f"scene_{new_scene_num:02d}.png"
            img_path = images_dir / img_filename
            img_config = {"image_generation": {"aspect_ratio": "16:9"}}
            img_prompt = f"Cinematic 16:9 film still. {visual_desc} Photorealistic, dramatic lighting, nature documentary style."

            # Character reference
            elements_dir = project_dir / "elements"
            try:
                show_settings = json.loads((Path("config/show_settings.json")).read_text())
                presenter_img = Path("config/presenter") / show_settings.get("presenter", {}).get("turnaround_image", "")
            except Exception:
                presenter_img = Path("")

            ref_path = None
            if scene_type == "presenter" and presenter_img.exists():
                ref_path = str(presenter_img)
            elif scene_type == "flashback":
                # For flashbacks, try to find character element images
                for elem_file in elements_dir.glob("*.png") if elements_dir.exists() else []:
                    if any(name in visual_desc.lower() for name in [elem_file.stem.replace("_", " ")]):
                        ref_path = str(elem_file)
                        break

            try:
                if ref_path:
                    story_engine.generate_image_with_ref(img_prompt, str(img_path), ref_path, config=img_config)
                else:
                    story_engine.generate_image(img_prompt, str(img_path), config=img_config)
                new_scene["scene_image"] = img_filename
                callback(f"✅ Image generated for Scene {new_scene_num}", "info")
            except Exception as img_err:
                callback(f"⚠️ Image generation failed: {str(img_err)[:100]}", "error")

            # Save
            sb_data["storyboard"] = scenes
            sb_data["total_scenes"] = len(scenes)
            with open(storyboard_path, "w") as f:
                json.dump(sb_data, f, indent=2, ensure_ascii=False)

            callback(f"✅ Storyboard saved! Now {len(scenes)} scenes.", "complete")

        except Exception as e:
            callback(f"❌ Insert failed: {str(e)[:200]}", "error")

    threading.Thread(target=insert_worker, daemon=True).start()
    return jsonify({"status": "inserting", "message": f"Inserting scene at position {insert_index + 1}..."})

@app.route("/api/project/<project_id>/analyze-intro", methods=["POST"])
def api_analyze_intro(project_id):
    """Generate intro storyboard scenes via Gemini."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404

    project_dir = get_project_dir(project_id)
    narration_path = project_dir / "narration.json"
    story_path = project_dir / "story.json"
    elements_path = project_dir / "elements.json"

    for path, name in [(narration_path, "Narration"), (story_path, "Story"), (elements_path, "Elements")]:
        if not path.exists():
            return jsonify({"error": f"{name} not found. Generate it first."}), 400

    with open(narration_path) as f:
        narration = json.load(f)
    with open(story_path) as f:
        story = json.load(f)
    with open(elements_path) as f:
        elements = json.load(f)

    # Load show settings for presenter
    show_settings = load_show_settings()
    presenter = show_settings.get("presenter", {})

    intro_text = narration.get("intro", {}).get("text", "")
    if not intro_text:
        return jsonify({"error": "No intro narration found"}), 400

    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)

    def run():
        try:
            callback("🎬 Analyzing intro narration...", "info")

            char = story.get("character", {})
            companion = char.get("companion", {})
            loc = story.get("location", {})

            element_refs = []
            for elem in elements:
                element_refs.append(f"@{elem.get('label', elem.get('element_id', '?'))} — {elem.get('description', '')[:80]}")
            element_context = "\n".join(element_refs)

            presenter_name = presenter.get("name", "Jack Harlan")

            callback(f"🧠 Building intro storyboard with presenter {presenter_name}...", "info")

            prompt = f"""You are a CINEMATIC STORYBOARD ANALYST for a survival documentary INTRO sequence.

INTRO NARRATION:
\"\"\"{intro_text}\"\"\"

STORY CONTEXT:
- Presenter: {presenter_name} (delivering the intro from inside a helicopter backseat, wearing aviation headset, speaking loud over rotor noise)
- Character: {char.get('name', 'Unknown')} — {char.get('description', '')}
- Companion: {companion.get('type', 'none')} — {companion.get('description', '')}
- Location: {loc.get('name', 'Unknown')} — {loc.get('terrain', 'wilderness')}

AVAILABLE ELEMENTS:
{element_context}

═══════════════════════════════════════════════════
YOUR TASK: Break this intro into 12-16 individual SCENES
═══════════════════════════════════════════════════

The intro has FOUR types of scenes. You MUST use all four:

1. **PRESENTER** — {presenter_name} in helicopter backseat, headset on, speaking loud over rotor noise to camera.
   He raises his voice over the deafening rotors (NOT yelling/shouting, just projecting).
   Camera is medium/close-up inside the helicopter cabin.

2. **BRIDGE** — Atmospheric shots of the landscape. Aerial views, wilderness, weather.
   NO people. Just environment. These separate presenter segments.

3. **FLASHBACK** — Scenes showing the backstory (the father, the past, the promise).
   Warm amber tones fading to cold. Emotional, literary.

4. **ANTICIPATORIO** — B-roll showing what's coming. The challenge ahead.
   The cabin site, the approaching winter, the tools, the isolation.

STRUCTURE RULES:
- Start with a BRIDGE (establishing aerial shot)
- Alternate between PRESENTER and BRIDGE/FLASHBACK/ANTICIPATORIO
- {presenter_name} delivers ALL narration. Non-presenter scenes are visual-only.
- FLASHBACK scenes appear when narration mentions the past/father/promise
- End with an ANTICIPATORIO scene (what's about to happen)
- Each scene: 5-12 seconds duration
- Total: ~90-110 seconds

OUTPUT FORMAT — Return a JSON array of scenes:
```json
[
  {{
    "scene_number": 1,
    "type": "bridge",
    "duration": "8s",
    "narration": "",
    "visual_description": "Aerial drone shot over vast Yukon wilderness at dawn. Frozen rivers cutting through dark boreal forest, snow-capped peaks on horizon.",
    "elements": [],
    "location_description": "yukon_aerial_dawn",
    "camera": "slow aerial push-in from ultra-wide",
    "sfx": "Wind, distant helicopter rotors approaching"
  }},
  {{
    "scene_number": 2,
    "type": "presenter",
    "duration": "12s",
    "narration": "In this first episode, we're heading into the wild Yukon wilderness...",
    "visual_description": "Medium shot from helicopter backseat. Presenter in headset, jaw set, turns to camera with energy. Raises voice over rotor noise.",
    "elements": ["{presenter_name}"],
    "location_description": "helicopter_interior_backseat",
    "camera": "medium shot, slight vibration from rotors",
    "sfx": "Deafening helicopter rotors, wind buffeting fuselage"
  }}
]
```

CRITICAL RULES:
- location_description must be a short snake_case identifier for the background image
- All images will be generated in 16:9 landscape format
- For presenter scenes, location is always "helicopter_interior_backseat"
- For flashback scenes, use warm/amber descriptors
- Each scene MUST have visual_description detailed enough to generate a video prompt
- Split narration naturally across presenter scenes (don't cram too much per scene)
- The emotional arc: excitement → gravity → emotion (father's death) → determination → anticipation

Return ONLY the JSON array. No other text."""

            callback("📡 Calling Gemini for intro analysis...", "info")

            response_text = story_engine.generate_text(prompt, temperature=0.3, max_tokens=8000, model="gemini-2.5-flash")

            callback("📋 Parsing storyboard response...", "info")

            # Extract JSON from response
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rindex("```")]
            text = text.strip()

            storyboard = json.loads(text)

            callback(f"✅ Generated {len(storyboard)} intro scenes", "info")

            # Save storyboard first (without images)
            intro_dir = project_dir / "production" / "intro"
            intro_dir.mkdir(parents=True, exist_ok=True)
            images_dir = intro_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            # Generate images for each scene
            callback(f"🎨 Generating images for {len(storyboard)} scenes...", "info")

            # Override config for 16:9 storyboard images
            img_config = {"image_generation": {"aspect_ratio": "16:9"}}

            # Build character reference map
            elements_dir = project_dir / "elements"
            show_settings = json.loads((Path("config/show_settings.json")).read_text())
            presenter_img = Path("config/presenter") / show_settings.get("presenter", {}).get("turnaround_image", "")
            
            for i, scene in enumerate(storyboard):
                scene_num = scene.get("scene_number", i + 1)
                img_filename = f"scene_{scene_num:02d}.png"
                img_path = images_dir / img_filename

                vis_desc = scene.get("visual_description", "")
                scene_type = scene.get("type", "bridge")
                
                if not vis_desc:
                    callback(f"  ⏭️ Scene {scene_num}: no visual description, skipping image", "info")
                    continue

                img_prompt = f"Cinematic 16:9 film still. {vis_desc} Photorealistic, dramatic lighting, nature documentary style."
                
                # Find best character reference for this scene
                ref_path = None
                scene_elements = scene.get("elements", [])
                
                if scene_type == "presenter" and presenter_img.exists():
                    ref_path = str(presenter_img)
                elif scene_elements:
                    # Try to find a matching element image
                    for elem_name in scene_elements:
                        elem_file = elem_name.lower().replace(" ", "_").replace("'", "").replace("(", "").replace(")", "") + ".png"
                        elem_path = elements_dir / elem_file
                        if elem_path.exists():
                            ref_path = str(elem_path)
                            break
                
                try:
                    callback(f"  🖼️ Scene {scene_num}/{len(storyboard)}: generating image{'  (with ref)' if ref_path else ''}...", "info")
                    if ref_path:
                        story_engine.generate_image_with_ref(img_prompt, str(img_path), ref_path, config=img_config)
                    else:
                        story_engine.generate_image(img_prompt, str(img_path), config=img_config)
                    scene["scene_image"] = img_filename
                    callback(f"  ✅ Scene {scene_num}: image saved", "info")
                except Exception as img_err:
                    callback(f"  ⚠️ Scene {scene_num}: image failed — {str(img_err)[:100]}", "error")
                    scene["scene_image"] = None

            # Save with image references
            result = {
                "storyboard": storyboard,
                "block_type": "intro",
                "total_scenes": len(storyboard),
                "total_duration": sum(int(s.get("duration", "8s").replace("s", "")) for s in storyboard)
            }

            with open(intro_dir / "storyboard.json", "w") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            generated_count = sum(1 for s in storyboard if s.get("scene_image"))
            callback(f"✅ Intro storyboard saved! {len(storyboard)} scenes, {generated_count} images, ~{result['total_duration']}s total", "complete")

        except Exception as e:
            callback(f"❌ Intro analysis failed: {str(e)}", "error")

    thread = threading.Thread(target=run)
    thread.start()



@app.route("/api/project/<project_id>/analyze-break", methods=["POST"])
def api_analyze_break(project_id):
    """Generate break storyboard scenes via Gemini."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404

    project_dir = get_project_dir(project_id)
    narration_path = project_dir / "narration.json"
    story_path = project_dir / "story.json"
    elements_path = project_dir / "elements.json"

    for path, name in [(narration_path, "Narration"), (story_path, "Story"), (elements_path, "Elements")]:
        if not path.exists():
            return jsonify({"error": f"{name} not found. Generate it first."}), 400

    data = request.get_json() or {}
    break_index = data.get("break_index", 0)

    with open(narration_path) as f:
        narration = json.load(f)
    with open(story_path) as f:
        story = json.load(f)
    with open(elements_path) as f:
        elements = json.load(f)

    # Load show settings for presenter
    show_settings = load_show_settings()
    presenter = show_settings.get("presenter", {})

    breaks = narration.get("breaks", [])
    if break_index >= len(breaks):
        return jsonify({"error": "Break index out of range"}), 400
    
    break_data = breaks[break_index]
    break_text = break_data.get("text", "")
    if not break_text:
        return jsonify({"error": "No break narration found"}), 400

    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)

    def run():
        try:
            callback(f"🎬 Analyzing break {break_index + 1} narration...", "info")

            char = story.get("character", {})
            companion = char.get("companion", {})
            loc = story.get("location", {})

            element_refs = []
            for elem in elements:
                element_refs.append(f"@{elem.get('label', elem.get('element_id', '?'))} — {elem.get('description', '')[:80]}")
            element_context = "\n".join(element_refs)

            presenter_name = presenter.get("name", "Jack Harlan")

            callback(f"🧠 Building break storyboard with presenter {presenter_name}...", "info")

            prompt = f"""You are a CINEMATIC STORYBOARD ANALYST for a survival documentary BREAK sequence.

BREAK NARRATION:
\"\"\"{break_text}\"\"\"

STORY CONTEXT:
- Presenter: {presenter_name} (delivering the mid-episode break hook/recap to camera. Can be outdoors or in studio/location)
- Character: {char.get('name', 'Unknown')} — {char.get('description', '')}
- Location: {loc.get('name', 'Unknown')} — {loc.get('terrain', 'wilderness')}

AVAILABLE ELEMENTS:
{element_context}

═══════════════════════════════════════════════════
YOUR TASK: Break this narration into 4-6 individual SCENES
═══════════════════════════════════════════════════

The break sequence relies mainly on the presenter recapping the challenge, mixed with visual b-roll (bridge/flashback) for emphasis.

STRUCTURE RULES:
- Start with a PRESENTER scene (delivering the hook).
- Alternate between PRESENTER and BRIDGE/FLASHBACK (b-roll showing the stakes/hardship).
- {presenter_name} delivers ALL narration. Non-presenter scenes are visual-only.
- Each scene: 5-10 seconds duration
- Total duration matches the break length (~30-45s)

OUTPUT FORMAT — Return a JSON array of scenes exactly matching this structure:
```json
[
  {{
    "scene_number": 1,
    "type": "presenter",
    "duration": "8s",
    "narration": "Erik has spent twenty days just clearing the mess...",
    "action": "Jack Harlan habla directo a cámara mientras camina entre los escombros nevados.",
    "visual_description": "Medium shot of {presenter_name} standing in snowy forest, speaking directly to camera with serious expression. Breath visible in cold air.",
    "elements": ["{presenter_name}"],
    "location_description": "snowy_forest",
    "camera": "medium shot, handheld slight movement",
    "sfx": "Wind howling, crunching snow"
  }},
  {{
    "scene_number": 2,
    "type": "bridge",
    "duration": "6s",
    "narration": "",
    "action": "Plano general de la cabaña destruida bajo la nieve.",
    "visual_description": "Wide establishing shot of the ruined cabin site buried in snow, looking bleak and impossible.",
    "elements": ["@Ruined Cabin"],
    "location_description": "ruined_cabin_wide",
    "camera": "slow pan right",
    "sfx": "Bleak wind"
  }}
]
```

CRITICAL RULES:
- location_description must be a short snake_case identifier for the background image
- All images will be generated in 16:9 landscape format
- Each scene MUST have visual_description detailed enough to generate a video prompt
- Each scene MUST have an `action` field describing what happens in the scene clearly.
- Split narration naturally across presenter scenes
- IDIOMA ESPAÑOL: La `narration`, `visual_description`, `action` y `sfx` DEBEN estar en español.

Return ONLY the JSON array. No other text."""

            callback("📡 Calling Gemini for break analysis...", "info")
            response_text = story_engine.generate_text(prompt, temperature=0.3, max_tokens=8000, model="gemini-2.5-flash")
            callback("📋 Parsing storyboard response...", "info")

            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rindex("```")]
            text = text.strip()

            storyboard = json.loads(text)
            callback(f"✅ Generated {len(storyboard)} break scenes", "info")

            break_dir = project_dir / "production" / f"break_{break_index + 1}"
            break_dir.mkdir(parents=True, exist_ok=True)
            images_dir = break_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            callback(f"🎨 Generating images for {len(storyboard)} scenes...", "info")
            img_config = {"image_generation": {"aspect_ratio": "16:9"}}
            elements_dir = project_dir / "elements"
            show_settings = json.loads((Path("config/show_settings.json")).read_text())
            presenter_img = Path("config/presenter") / show_settings.get("presenter", {}).get("turnaround_image", "")
            
            for i, scene in enumerate(storyboard):
                scene_num = scene.get("scene_number", i + 1)
                img_filename = f"scene_{scene_num:02d}.png"
                img_path = images_dir / img_filename
                vis_desc = scene.get("visual_description", "")
                scene_type = scene.get("type", "bridge")
                
                if not vis_desc:
                    callback(f"  ⏭️ Scene {scene_num}: no visual description, skipping image", "info")
                    continue

                img_prompt = f"Cinematic 16:9 film still. {vis_desc} Photorealistic, dramatic lighting, nature documentary style."
                ref_path = None
                scene_elements = scene.get("elements", [])
                
                if scene_type == "presenter" and presenter_img.exists():
                    ref_path = str(presenter_img)
                elif scene_elements:
                    for elem_name in scene_elements:
                        elem_file = elem_name.lower().replace(" ", "_").replace("'", "").replace("(", "").replace(")", "") + ".png"
                        elem_path = elements_dir / elem_file
                        if elem_path.exists():
                            ref_path = str(elem_path)
                            break
                
                try:
                    callback(f"  🖼️ Scene {scene_num}/{len(storyboard)}: generating image{'  (with ref)' if ref_path else ''}...", "info")
                    if ref_path:
                        story_engine.generate_image_with_ref(img_prompt, str(img_path), ref_path, config=img_config)
                    else:
                        story_engine.generate_image(img_prompt, str(img_path), config=img_config)
                    scene["scene_image"] = img_filename
                    callback(f"  ✅ Scene {scene_num}: image saved", "info")
                except Exception as img_err:
                    callback(f"  ⚠️ Scene {scene_num}: image failed — {str(img_err)[:100]}", "error")
                    scene["scene_image"] = None

            result = {
                "storyboard": storyboard,
                "block_type": "break",
                "total_scenes": len(storyboard),
                "total_duration": sum(int(str(s.get("duration", "8s")).replace("s", "")) for s in storyboard)
            }

            with open(break_dir / "storyboard.json", "w") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            generated_count = sum(1 for s in storyboard if s.get("scene_image"))
            callback(f"✅ Break {break_index + 1} storyboard saved! {len(storyboard)} scenes, {generated_count} images.", "complete")

        except Exception as e:
            callback(f"❌ Break analysis failed: {str(e)}", "error")

    thread = threading.Thread(target=run)
    thread.start()

    return jsonify({"status": "analyzing", "block_type": "break"})


@app.route("/api/project/<project_id>/analyze-close", methods=["POST"])
def api_analyze_close(project_id):
    """Generate close storyboard scenes via Gemini."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404

    project_dir = get_project_dir(project_id)
    narration_path = project_dir / "narration.json"
    story_path = project_dir / "story.json"
    elements_path = project_dir / "elements.json"

    for path, name in [(narration_path, "Narration"), (story_path, "Story"), (elements_path, "Elements")]:
        if not path.exists():
            return jsonify({"error": f"{name} not found. Generate it first."}), 400

    with open(narration_path) as f:
        narration = json.load(f)
    with open(story_path) as f:
        story = json.load(f)
    with open(elements_path) as f:
        elements = json.load(f)

    # Load show settings for presenter
    show_settings = load_show_settings()
    presenter = show_settings.get("presenter", {})

    close_text = narration.get("close", {}).get("text", "")
    if not close_text:
        return jsonify({"error": "No close narration found"}), 400

    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)

    def run():
        try:
            callback("🎬 Analyzing close narration...", "info")

            char = story.get("character", {})
            loc = story.get("location", {})

            element_refs = []
            for elem in elements:
                element_refs.append(f"@{elem.get('label', elem.get('element_id', '?'))} — {elem.get('description', '')[:80]}")
            element_context = "\n".join(element_refs)

            presenter_name = presenter.get("name", "Jack Harlan")

            callback(f"🧠 Building close storyboard with presenter {presenter_name}...", "info")

            prompt = f"""You are a CINEMATIC STORYBOARD ANALYST for a survival documentary CLOSE sequence.

CLOSE NARRATION:
\"\"\"{close_text}\"\"\"

STORY CONTEXT:
- Presenter: {presenter_name} (delivering the outro/conclusion to camera)
- Character: {char.get('name', 'Unknown')} — {char.get('description', '')}
- Location: {loc.get('name', 'Unknown')} — {loc.get('terrain', 'wilderness')}

AVAILABLE ELEMENTS:
{element_context}

═══════════════════════════════════════════════════
YOUR TASK: Break this narration into 5-8 individual SCENES
═══════════════════════════════════════════════════

The close sequence wraps up the episode, highlighting the character's triumph/survival.

STRUCTURE RULES:
- Start with a PRESENTER scene (delivering the conclusion).
- Mix with BRIDGE/RECAP (b-roll showing the finished shelter, the survivor resting, wide shots of the environment).
- End with a final establishing wide shot or presenter sign-off.
- {presenter_name} delivers ALL narration. Non-presenter scenes are visual-only.
- Each scene: 5-10 seconds duration

OUTPUT FORMAT — Return a JSON array of scenes exactly matching this structure:
```json
[
  {{
    "scene_number": 1,
    "type": "presenter",
    "duration": "10s",
    "narration": "Ninety days. Erik did the impossible...",
    "action": "Jack Harlan habla directo a cámara de pie junto al campamento al atardecer.",
    "visual_description": "Medium shot of {presenter_name} standing near a crackling campfire at dusk, looking into camera with respect.",
    "elements": ["{presenter_name}"],
    "location_description": "dusk_campfire",
    "camera": "medium shot, static",
    "sfx": "Crackling fire, gentle wind"
  }}
]
```

CRITICAL RULES:
- location_description must be a short snake_case identifier for the background image
- All images will be generated in 16:9 landscape format
- Each scene MUST have visual_description detailed enough to generate a video prompt
- Each scene MUST have an `action` field describing what happens in the scene clearly.
- Split narration naturally across presenter scenes
- IDIOMA ESPAÑOL: La `narration`, `visual_description`, `action` y `sfx` DEBEN estar en español.

Return ONLY the JSON array. No other text."""

            callback("📡 Calling Gemini for close analysis...", "info")
            response_text = story_engine.generate_text(prompt, temperature=0.3, max_tokens=8000, model="gemini-2.5-flash")
            callback("📋 Parsing storyboard response...", "info")

            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                elif "```" in text:
                    text = text[:text.rindex("```")]
            text = text.strip()

            storyboard = json.loads(text)
            callback(f"✅ Generated {len(storyboard)} close scenes", "info")

            close_dir = project_dir / "production" / "close"
            close_dir.mkdir(parents=True, exist_ok=True)
            images_dir = close_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            callback(f"🎨 Generating images for {len(storyboard)} scenes...", "info")
            img_config = {"image_generation": {"aspect_ratio": "16:9"}}
            elements_dir = project_dir / "elements"
            show_settings = json.loads((Path("config/show_settings.json")).read_text())
            presenter_img = Path("config/presenter") / show_settings.get("presenter", {}).get("turnaround_image", "")
            
            for i, scene in enumerate(storyboard):
                scene_num = scene.get("scene_number", i + 1)
                img_filename = f"scene_{scene_num:02d}.png"
                img_path = images_dir / img_filename
                vis_desc = scene.get("visual_description", "")
                scene_type = scene.get("type", "bridge")
                
                if not vis_desc:
                    callback(f"  ⏭️ Scene {scene_num}: no visual description, skipping image", "info")
                    continue

                img_prompt = f"Cinematic 16:9 film still. {vis_desc} Photorealistic, dramatic lighting, nature documentary style."
                ref_path = None
                scene_elements = scene.get("elements", [])
                
                if scene_type == "presenter" and presenter_img.exists():
                    ref_path = str(presenter_img)
                elif scene_elements:
                    for elem_name in scene_elements:
                        elem_file = elem_name.lower().replace(" ", "_").replace("'", "").replace("(", "").replace(")", "") + ".png"
                        elem_path = elements_dir / elem_file
                        if elem_path.exists():
                            ref_path = str(elem_path)
                            break
                
                try:
                    callback(f"  🖼️ Scene {scene_num}/{len(storyboard)}: generating image{'  (with ref)' if ref_path else ''}...", "info")
                    if ref_path:
                        story_engine.generate_image_with_ref(img_prompt, str(img_path), ref_path, config=img_config)
                    else:
                        story_engine.generate_image(img_prompt, str(img_path), config=img_config)
                    scene["scene_image"] = img_filename
                    callback(f"  ✅ Scene {scene_num}: image saved", "info")
                except Exception as img_err:
                    callback(f"  ⚠️ Scene {scene_num}: image failed — {str(img_err)[:100]}", "error")
                    scene["scene_image"] = None

            result = {
                "storyboard": storyboard,
                "block_type": "close",
                "total_scenes": len(storyboard),
                "total_duration": sum(int(str(s.get("duration", "8s")).replace("s", "")) for s in storyboard)
            }

            with open(close_dir / "storyboard.json", "w") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            generated_count = sum(1 for s in storyboard if s.get("scene_image"))
            callback(f"✅ Close storyboard saved! {len(storyboard)} scenes, {generated_count} images.", "complete")

        except Exception as e:
            callback(f"❌ Close analysis failed: {str(e)}", "error")

    thread = threading.Thread(target=run)
    thread.start()

    return jsonify({"status": "analyzing", "block_type": "close"})


@app.route("/api/project/<project_id>/analyze-chapter", methods=["POST"])
def api_analyze_chapter(project_id):
    """Run Cinematic Analyzer on a specific chapter. Returns storyboard for review."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    project_dir = get_project_dir(project_id)
    
    story_path = project_dir / "story.json"
    narration_path = project_dir / "narration.json"
    elements_path = project_dir / "elements.json"
    
    for path, name in [(story_path, "Story"), (narration_path, "Narration"), (elements_path, "Elements")]:
        if not path.exists():
            return jsonify({"error": f"{name} not found. Generate it first."}), 400
    
    with open(story_path) as f:
        story = json.load(f)
    with open(narration_path) as f:
        narration = json.load(f)
    with open(elements_path) as f:
        elements = json.load(f)
    
    data = request.get_json() or {}
    chapter_index = data.get("chapter_index", 0)
    
    # Extract chapter narration
    phases = narration.get("phases", [])
    # Group phases by chapter
    chapters = {}
    for phase in phases:
        ch_name = phase.get("chapter", phase.get("phase_name", "Unknown"))
        if ch_name not in chapters:
            chapters[ch_name] = []
        chapters[ch_name].append(phase)
    
    chapter_names = list(chapters.keys())
    if chapter_index >= len(chapter_names):
        return jsonify({"error": f"Chapter index {chapter_index} out of range (max {len(chapter_names)-1})"}), 400
    
    # Combine all phase narrations for this chapter
    ch_name = chapter_names[chapter_index]
    chapter_phases = chapters[ch_name]
    chapter_narration = "\n\n".join([p.get("narration", "") for p in chapter_phases if p.get("narration")])
    
    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)
    
    def run():
        try:
            analysis = story_engine.cinematic_analyze_chapter(
                story, chapter_narration, chapter_index, elements, progress_callback=callback
            )
            
            storyboard = analysis.get("storyboard", [])
            callback(f"📊 Gemini returned {len(storyboard)} scenes in storyboard array (total_scenes field: {analysis.get('total_scenes', '?')})", "info")

            # ─── NORMALIZE FIELDS (chapter format → standard format) ───
            for i, scene in enumerate(storyboard):
                # scene_num → scene_number
                if "scene_num" in scene and "scene_number" not in scene:
                    scene["scene_number"] = scene.pop("scene_num")
                if "scene_number" not in scene:
                    scene["scene_number"] = i + 1
                # narration_excerpt → narration
                if "narration_excerpt" in scene and "narration" not in scene:
                    scene["narration"] = scene.pop("narration_excerpt") or ""
                # Ensure visual_description exists (copy from action if missing)
                if not scene.get("visual_description") and scene.get("action"):
                    scene["visual_description"] = scene["action"]
                # Smart duration assignment (override Gemini's defaults)
                action_lower = (scene.get("action", "") or "").lower()
                scene_type = scene.get("type", "narrated")
                has_tools = bool(scene.get("tools"))
                
                # Keywords indicating complex processes that need more time
                complex_keywords = ["constru", "monta", "ensambla", "tala", "clava", "sierra", 
                                    "corta", "encaja", "ajust", "asegura", "levant", "coloca",
                                    "build", "assembl", "chop", "saw", "nail", "carv"]
                is_complex = any(kw in action_lower for kw in complex_keywords)
                
                if scene_type == "bridge":
                    scene["duration"] = "8s" if has_tools else "5s"
                elif is_complex or has_tools:
                    scene["duration"] = "12s"
                else:
                    scene["duration"] = "10s"

            callback(f"✅ Normalized {len(storyboard)} scenes", "info")

            # Validate storyboard
            validation = story_engine.validate_storyboard(
                storyboard, chapter_narration, progress_callback=callback
            )
            analysis["validation"] = validation
            
            # Save storyboard + validation for review
            storyboard_dir = project_dir / "production" / f"chapter_{chapter_index + 1}"
            storyboard_dir.mkdir(parents=True, exist_ok=True)
            images_dir = storyboard_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            # ─── GENERATE SCENE IMAGES ───
            # Build story context for visual consistency
            loc_name = story.get("location", {}).get("name", "remote wilderness")
            terrain = story.get("location", {}).get("terrain", "wilderness")
            climate = story.get("location", {}).get("climate", "")
            season = story.get("timeline", {}).get("season", "")
            story_context = f"Setting: {loc_name}, {terrain}."
            if climate:
                story_context += f" {climate}."
            if season:
                story_context += f" Season: {season}."

            callback(f"🎨 Generating images for {len(storyboard)} scenes...", "info")
            callback(f"  📍 Context: {story_context}", "info")
            img_config = {"image_generation": {"aspect_ratio": "16:9"}}

            # Build character reference map
            elements_dir = project_dir / "elements"

            for i, scene in enumerate(storyboard):
                scene_num = scene.get("scene_number", i + 1)
                img_filename = f"scene_{scene_num:02d}.png"
                img_path = images_dir / img_filename

                vis_desc = scene.get("visual_description", scene.get("action", ""))
                if not vis_desc:
                    callback(f"  ⏭️ Scene {scene_num}: no visual description, skipping image", "info")
                    continue

                # Build per-scene environment details
                scene_env = ""
                weather = scene.get("weather", "")
                time_of_day = scene.get("time_of_day", "")
                if weather:
                    scene_env += f" Weather: {weather}."
                if time_of_day:
                    scene_env += f" Time: {time_of_day}."

                # Build narration context (what the story is about at this moment)
                narration = scene.get("narration", "") or ""
                narr_context = f" Story context: \"{narration[:200]}\"." if narration else ""

                # Build previous scene context (what just happened visually)
                prev_context = ""
                if i > 0:
                    prev_scene = storyboard[i - 1]
                    prev_desc = prev_scene.get("visual_description", prev_scene.get("action", ""))
                    if prev_desc:
                        prev_context = f" Previous shot: {prev_desc[:150]}."

                img_prompt = f"Cinematic 16:9 film still. {story_context}{scene_env}{narr_context}{prev_context} Shot: {vis_desc} Photorealistic, dramatic lighting, nature documentary style."

                # Find best character reference for this scene
                ref_path = None
                scene_elements = scene.get("elements", [])
                for elem_name in scene_elements:
                    # Clean up @prefix if present
                    clean_name = elem_name.lstrip("@").lower().replace(" ", "_").replace("'", "").replace("(", "").replace(")", "")
                    elem_file = clean_name + ".png"
                    elem_path = elements_dir / elem_file
                    if elem_path.exists():
                        ref_path = str(elem_path)
                        break

                max_retries = 3
                for attempt in range(max_retries + 1):
                    try:
                        if attempt == 0:
                            callback(f"  🖼️ Scene {scene_num}/{len(storyboard)}: generating image{'  (with ref)' if ref_path else ''}...", "info")
                        else:
                            callback(f"  🔄 Scene {scene_num}: retry {attempt}/{max_retries}...", "info")
                        if ref_path:
                            story_engine.generate_image_with_ref(img_prompt, str(img_path), ref_path, config=img_config)
                        else:
                            story_engine.generate_image(img_prompt, str(img_path), config=img_config)
                        scene["scene_image"] = img_filename
                        callback(f"  ✅ Scene {scene_num}: image saved", "info")
                        break
                    except Exception as img_err:
                        err_str = str(img_err)
                        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                            if attempt < max_retries:
                                wait = 30 * (attempt + 1)
                                callback(f"  ⏳ Scene {scene_num}: rate limited, waiting {wait}s...", "info")
                                import time as _time
                                _time.sleep(wait)
                                continue
                        callback(f"  ⚠️ Scene {scene_num}: image failed — {err_str[:100]}", "info")
                        scene["scene_image"] = None
                        break

            # Save final result
            generated_count = sum(1 for s in storyboard if s.get("scene_image"))
            
            with open(storyboard_dir / "storyboard.json", "w") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            if validation["valid"]:
                callback(f"✅ Chapter {chapter_index + 1} complete! {len(storyboard)} scenes, {generated_count} images. Score: {validation['score']}/100", "complete")
            else:
                callback(f"✅ Chapter {chapter_index + 1} complete! {len(storyboard)} scenes, {generated_count} images. (Validation: {validation['total_errors']} suggestion(s), score {validation['score']}/100)", "complete")
        except Exception as e:
            callback(f"❌ Cinematic analysis failed: {str(e)}", "error")
    
    thread = threading.Thread(target=run)
    thread.start()
    
    return jsonify({
        "status": "analyzing",
        "chapter_name": ch_name,
        "chapter_index": chapter_index
    })





@app.route("/api/project/<project_id>/storyboard/<block_folder>", methods=["PUT"])
def api_save_storyboard(project_id, block_folder):
    """Save storyboard data for any block (intro, chapter_1, break_1, close)."""
    project_dir = get_project_dir(project_id)
    storyboard_path = project_dir / "production" / block_folder / "storyboard.json"

    if not storyboard_path.exists():
        return jsonify({"error": "Storyboard not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Read existing file and update storyboard array
    with open(storyboard_path) as f:
        existing = json.load(f)

    existing["storyboard"] = data.get("storyboard", existing.get("storyboard", []))

    with open(storyboard_path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "saved"})


@app.route("/api/project/<project_id>/storyboard/<int:chapter_index>", methods=["PUT"])
def api_update_storyboard(project_id, chapter_index):
    """Update the storyboard table after user review (add/remove/reorder scenes)."""
    project_dir = get_project_dir(project_id)
    storyboard_path = project_dir / "production" / f"chapter_{chapter_index + 1}" / "storyboard.json"
    
    if not storyboard_path.exists():
        return jsonify({"error": "Storyboard not found. Run analyze-chapter first."}), 404
    
    updated = request.get_json()
    if not updated:
        return jsonify({"error": "No data provided"}), 400
    
    with open(storyboard_path, "w") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)
    
    return jsonify({"status": "updated", "scenes": len(updated.get("storyboard", []))})


@app.route("/api/project/<project_id>/generate-chapter-production", methods=["POST"])
def api_generate_chapter_production(project_id):
    """Run the full production pipeline for a chapter (state tracking + images + prompts)."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    project_dir = get_project_dir(project_id)
    
    story_path = project_dir / "story.json"
    narration_path = project_dir / "narration.json"
    elements_path = project_dir / "elements.json"
    
    for path, name in [(story_path, "Story"), (narration_path, "Narration"), (elements_path, "Elements")]:
        if not path.exists():
            return jsonify({"error": f"{name} not found. Generate it first."}), 400
    
    with open(story_path) as f:
        story = json.load(f)
    with open(narration_path) as f:
        narration = json.load(f)
    with open(elements_path) as f:
        elements = json.load(f)
    
    data = request.get_json() or {}
    chapter_index = data.get("chapter_index", 0)
    
    # Extract chapter narration
    phases = narration.get("phases", [])
    chapters = {}
    for phase in phases:
        ch_name = phase.get("chapter", phase.get("phase_name", "Unknown"))
        if ch_name not in chapters:
            chapters[ch_name] = []
        chapters[ch_name].append(phase)
    
    chapter_names = list(chapters.keys())
    if chapter_index >= len(chapter_names):
        return jsonify({"error": f"Chapter index {chapter_index} out of range"}), 400
    
    ch_name = chapter_names[chapter_index]
    chapter_phases = chapters[ch_name]
    chapter_narration = "\n\n".join([p.get("narration", "") for p in chapter_phases if p.get("narration")])
    
    # Get break text if available
    breaks = narration.get("breaks", [])
    break_text = None
    if chapter_index < len(breaks):
        break_text = breaks[chapter_index].get("text", "")
    
    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)
    
    def run():
        try:
            production = story_engine.generate_chapter_production(
                story, chapter_narration, chapter_index, elements,
                str(project_dir), break_text=break_text, progress_callback=callback
            )
            
            # Save production package
            story_engine.build_production_package(
                production, str(project_dir), chapter_index, progress_callback=callback
            )
            
            # Update project metadata
            meta.setdefault("production_chapters", {})[str(chapter_index)] = {
                "status": "complete",
                "total_scenes": production["metadata"]["total_scenes"],
                "duration": production["metadata"]["estimated_duration_formatted"]
            }
            save_project_metadata(project_id, meta)
            
            callback(f"\u2705 Chapter {chapter_index + 1} production complete!", "complete")
        except Exception as e:
            callback(f"\u274c Production failed: {str(e)}", "error")
    
    thread = threading.Thread(target=run)
    thread.start()
    
    return jsonify({
        "status": "generating",
        "chapter_name": ch_name,
        "chapter_index": chapter_index
    })


@app.route("/api/project/<project_id>/locations/<filename>")
def serve_location(project_id, filename):
    """Serve a generated location image."""
    project_dir = get_project_dir(project_id)
    return send_from_directory(project_dir / "locations", filename)


@app.route("/api/project/<project_id>/production/<int:chapter_index>/<filename>")
def serve_production_file(project_id, chapter_index, filename):
    """Serve a production package file (prompts.json, storyboard.json, etc.)."""
    project_dir = get_project_dir(project_id)
    prod_dir = project_dir / "production" / f"chapter_{chapter_index + 1}"
    
    if not (prod_dir / filename).exists():
        return jsonify({"error": "File not found"}), 404
    
    return send_from_directory(prod_dir, filename)



@app.route("/api/project/<project_id>/generate-narration", methods=["POST"])
def api_generate_narration(project_id):
    """Generate narration (intro, phases, breaks, close) from story."""
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    project_dir = get_project_dir(project_id)
    
    story_path = project_dir / "story.json"
    if not story_path.exists():
        return jsonify({"error": "Story not found. Generate story first."}), 400
    with open(story_path) as f:
        story = json.load(f)
    
    _progress_streams[project_id] = []
    callback = progress_callback_factory(project_id)
    
    def run():
        try:
            narration = story_engine.generate_narration(story, callback)
            
            with open(project_dir / "narration.json", "w") as f:
                json.dump(narration, f, indent=2, ensure_ascii=False)
            
            meta["status"] = "narration_generated"
            if "narration" not in meta.get("steps_completed", []):
                meta.setdefault("steps_completed", []).append("narration")
            save_project_metadata(project_id, meta)
            
            callback("✅ Narration saved!", "complete")
        except Exception as e:
            callback(f"❌ Error: {str(e)}", "error")
    
    thread = threading.Thread(target=run)
    thread.start()
    
    return jsonify({"status": "generating", "message": "Narration generation started"})




# =============================================================================
# ROUTES — SSE Progress Stream
# =============================================================================

@app.route("/api/project/<project_id>/progress")
def progress_stream(project_id):
    """SSE endpoint for real-time progress updates."""
    # Only initialize if no stream exists yet (don't clear mid-generation!)
    if project_id not in _progress_streams:
        _progress_streams[project_id] = []
    
    def generate():
        last_index = 0
        heartbeat = 0
        
        while True:
            messages = _progress_streams.get(project_id, [])
            
            if last_index < len(messages):
                for msg in messages[last_index:]:
                    yield f"data: {json.dumps(msg)}\n\n"
                    # If complete or error, stop
                    if msg.get("type") in ("complete", "error"):
                        return
                last_index = len(messages)
            
            # Heartbeat every 15 seconds
            heartbeat += 1
            if heartbeat % 30 == 0:
                yield f": heartbeat\n\n"
            
            time.sleep(0.5)
    
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# =============================================================================
# ROUTES — Show Settings (Global Presenter Config)
# =============================================================================

CONFIG_DIR = Path(__file__).parent / "config"
SHOW_SETTINGS_FILE = CONFIG_DIR / "show_settings.json"
PRESENTER_DIR = CONFIG_DIR / "presenter"
PRESENTER_DIR.mkdir(parents=True, exist_ok=True)


def load_show_settings():
    """Load show settings from JSON."""
    if SHOW_SETTINGS_FILE.exists():
        with open(SHOW_SETTINGS_FILE) as f:
            return json.load(f)
    return {"presenter": {"name": "", "turnaround_image": "", "elevenlabs_voice_id": "", "elevenlabs_model": "eleven_v3", "elevenlabs_stability": 0.5, "elevenlabs_speed": 0.75}}


def save_show_settings(data):
    """Save show settings to JSON."""
    with open(SHOW_SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


@app.route("/api/show-settings")
def get_show_settings():
    """Get global show settings."""
    return jsonify(load_show_settings())


@app.route("/api/show-settings", methods=["POST"])
def post_show_settings():
    """Save global show settings."""
    data = request.get_json()
    settings = load_show_settings()
    # Update only provided fields
    presenter = settings.get("presenter", {})
    for key in ["name", "elevenlabs_voice_id", "elevenlabs_model", "elevenlabs_stability", "elevenlabs_speed"]:
        if key in data:
            presenter[key] = data[key]
    settings["presenter"] = presenter
    save_show_settings(settings)
    return jsonify({"status": "saved", "settings": settings})


@app.route("/api/show-settings/upload", methods=["POST"])
def upload_presenter_image():
    """Upload presenter turnaround image."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    # Save with a clean name
    from werkzeug.utils import secure_filename
    filename = secure_filename(f.filename)
    filepath = PRESENTER_DIR / filename
    f.save(filepath)
    # Update settings
    settings = load_show_settings()
    settings["presenter"]["turnaround_image"] = filename
    save_show_settings(settings)
    return jsonify({"status": "uploaded", "filename": filename})


@app.route("/config/presenter/<filename>")
def serve_presenter_image(filename):
    """Serve presenter reference images."""
    return send_from_directory(PRESENTER_DIR, filename)


# =============================================================================
# ROUTES — Delete
# =============================================================================

@app.route("/api/diversity")
def api_diversity():
    """Get diversity tracker stats — what's been used and what's recommended."""
    recs = diversity_tracker.get_recommendations()
    return jsonify(recs)


@app.route("/api/project/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    """Delete a project and all its files."""
    import shutil
    project_dir = get_project_dir(project_id)
    if project_dir.exists():
        shutil.rmtree(project_dir)
    return jsonify({"status": "deleted"})


@app.route("/api/project/<project_id>/download-script")
def download_script(project_id):
    """Download narration as a .txt script file."""
    import re as _re
    meta = load_project_metadata(project_id)
    if not meta:
        return jsonify({"error": "Project not found"}), 404
    
    project_dir = get_project_dir(project_id)
    narration_path = project_dir / "narration.json"
    if not narration_path.exists():
        return jsonify({"error": "No narration found"}), 404
    
    with open(narration_path) as f:
        narration = json.load(f)
    
    intro = narration.get("intro", {})
    phases = narration.get("phases", [])
    breaks = narration.get("breaks", [])
    close = narration.get("close", {})
    summary = narration.get("summary", {})
    
    lines = []
    lines.append("THE LAST SHELTER — NARRATION SCRIPT")
    lines.append("=" * 50)
    lines.append(f"Episode: {meta.get('title', 'Unknown')}")
    lines.append(f"Total Words: {summary.get('total_words', 0)} | Voiceover: {summary.get('voiceover_words', 0)} | Presenter: {summary.get('breaks_words', 0)}")
    lines.append(f"Phases: {summary.get('phases_count', 0)} | Breaks: {summary.get('breaks_count', 0)}")
    lines.append("=" * 50)
    lines.append("")
    
    if intro.get("text"):
        lines.append(f"=== PRESENTER INTRO ({intro.get('duration_seconds', 0)}s) ===")
        lines.append("")
        lines.append(intro["text"])
        lines.append("")
    
    break_num = 0
    for i, p in enumerate(phases):
        sr = f"Scenes {p['scene_range'][0]}-{p['scene_range'][1]}" if p.get("scene_range") else ""
        clean = _re.sub(r'^Phase\s*\d+\s*[:.]?\s*', '', p.get('phase_name', f'Phase {i+1}')).strip()
        lines.append("-" * 50)
        lines.append(f"=== {clean} ({p.get('word_count', 0)} words, {sr}) ===")
        lines.append("")
        lines.append(p.get("narration", "[Failed to generate]"))
        lines.append("")
        
        ba = next((b for b in breaks if b.get("after_phase_index") == i), None)
        if ba:
            break_num += 1
            lines.append("-" * 50)
            lines.append(f"--- PRESENTER BREAK #{break_num} ---")
            lines.append("")
            lines.append(f'"{ba.get("text", "")}"')
            lines.append("")
    
    if close.get("text"):
        lines.append("-" * 50)
        lines.append(f"=== PRESENTER OUTRO ({close.get('duration_seconds', 0)}s) ===")
        lines.append("")
        lines.append(close["text"])
        if close.get("teaser"):
            lines.append("")
            lines.append(f"Next: {close['teaser']}")
    
    script = "\n".join(lines)
    
    safe_title = _re.sub(r'[^a-zA-Z0-9\s]', '', meta.get('title', 'script')).strip()
    safe_title = _re.sub(r'\s+', '-', safe_title).lower()
    filename = f"{safe_title}.txt"
    
    return Response(
        script,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )



# MAIN
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
