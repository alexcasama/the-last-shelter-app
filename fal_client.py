"""
fal_client.py — fal.ai API integration for Kling video generation.

Uses the REST API directly (no SDK dependency).
Queue-based: submit → poll → result.
"""

import os
import time
import base64
import requests
from pathlib import Path

FAL_API_KEY = os.environ.get("FAL_KEY", "")
FAL_BASE_URL = "https://queue.fal.run"

# Kling V3 Pro image-to-video endpoint (higher quality, $0.392/s vs $0.224/s)
KLING_I2V_ENDPOINT = "fal-ai/kling-video/v3/pro/image-to-video"
KLING_MODEL_ID = "fal-ai/kling-video"  # Base model ID (without subpath) for status/result


def _headers():
    return {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type": "application/json",
    }


def image_to_data_uri(image_path):
    """Convert a local image file to a base64 data URI."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Detect MIME type
    suffix = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    mime = mime_map.get(suffix, "image/png")
    
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    
    return f"data:{mime};base64,{b64}"


def upload_image_to_fal(image_path):
    """Upload a local image to fal.ai CDN and return a public URL.
    
    Falls back to data URI if upload fails.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    suffix = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    content_type = mime_map.get(suffix, "application/octet-stream")
    
    try:
        # Step 1: Get upload URL
        initiate_res = requests.post(
            "https://rest.alpha.fal.ai/storage/upload/initiate",
            headers=_headers(),
            json={"file_name": path.name, "content_type": content_type}
        )
        
        if initiate_res.status_code == 200:
            data = initiate_res.json()
            upload_url = data.get("upload_url")
            file_url = data.get("file_url")
            
            # Step 2: Upload the file
            with open(path, "rb") as f:
                upload_res = requests.put(
                    upload_url,
                    headers={"Content-Type": content_type},
                    data=f.read()
                )
            
            if upload_res.status_code in (200, 201):
                return file_url
    except Exception as e:
        print(f"[fal_client] Upload failed, falling back to data URI: {e}")
    
    # Fallback: use data URI
    return image_to_data_uri(image_path)


def submit_video_generation(
    prompt,
    start_image_path,
    end_image_path=None,
    duration=5,
    generate_audio=True,
):
    """
    Submit a video generation request to fal.ai Kling 3 Pro Standard.
    
    Args:
        prompt: Video prompt text (Kling 3 style)
        start_image_path: Local path to start frame image
        end_image_path: Optional local path to end frame image
        duration: Video duration in seconds (3-15)
        generate_audio: Whether to generate native audio
        
    Returns:
        dict with 'request_id' for polling
    """
    # Upload images
    start_url = upload_image_to_fal(start_image_path)
    end_url = upload_image_to_fal(end_image_path) if end_image_path else None
    
    payload = {
        "prompt": prompt,
        "image_url": start_url,
        "duration": str(int(duration)),
        "generate_audio": generate_audio,
    }
    
    if end_url:
        payload["end_image_url"] = end_url
    
    response = requests.post(
        f"{FAL_BASE_URL}/{KLING_I2V_ENDPOINT}",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    
    if response.status_code not in (200, 201, 202):
        raise Exception(f"fal.ai submit failed ({response.status_code}): {response.text[:500]}")
    
    result = response.json()
    request_id = result.get("request_id")
    if not request_id:
        raise Exception(f"No request_id in response: {result}")
    
    return {
        "request_id": request_id,
        "status": "IN_QUEUE",
        "status_url": result.get("status_url", f"{FAL_BASE_URL}/{KLING_MODEL_ID}/requests/{request_id}/status"),
        "response_url": result.get("response_url", f"{FAL_BASE_URL}/{KLING_MODEL_ID}/requests/{request_id}"),
    }


def check_status(request_id, status_url=None):
    """Check the status of a video generation request.
    
    Returns:
        dict with 'status': 'IN_QUEUE' | 'IN_PROGRESS' | 'COMPLETED'
        and optionally 'logs' and 'queue_position'
    """
    url = status_url or f"{FAL_BASE_URL}/{KLING_MODEL_ID}/requests/{request_id}/status"
    response = requests.get(
        url,
        headers=_headers(),
        params={"logs": "1"},
        timeout=15,
    )
    
    if response.status_code != 200:
        return {"status": "UNKNOWN", "error": response.text[:200]}
    
    return response.json()


def get_result(request_id, response_url=None):
    """Get the result of a completed video generation request.
    
    Returns:
        dict with 'video': {'url': '...', 'file_size': ..., 'content_type': '...'}
    """
    url = response_url or f"{FAL_BASE_URL}/{KLING_MODEL_ID}/requests/{request_id}"
    response = requests.get(
        url,
        headers=_headers(),
        timeout=30,
    )
    
    if response.status_code != 200:
        raise Exception(f"fal.ai result failed ({response.status_code}): {response.text[:300]}")
    
    data = response.json()
    # Queue API wraps result under "response" key
    if "response" in data:
        return data["response"]
    return data


def wait_for_completion(request_id, status_url=None, response_url=None,
                        timeout=600, poll_interval=10, progress_callback=None):
    """Poll until the video generation is complete or timeout.
    
    Args:
        request_id: The fal.ai request_id
        status_url: Direct status URL from submit response
        response_url: Direct response URL from submit response
        timeout: Max seconds to wait
        poll_interval: Seconds between status checks
        progress_callback: Optional callback(message, type)
        
    Returns:
        dict with result data including video URL
    """
    start_time = time.time()
    last_status = ""
    
    while time.time() - start_time < timeout:
        status_data = check_status(request_id, status_url=status_url)
        status = status_data.get("status", "UNKNOWN")
        
        if status != last_status:
            last_status = status
            if progress_callback:
                queue_pos = status_data.get("queue_position", "?")
                progress_callback(
                    f"⏳ Video status: {status} (queue position: {queue_pos})",
                    "info"
                )
        
        if status == "COMPLETED":
            return get_result(request_id, response_url=response_url)
        
        if status in ("FAILED", "CANCELLED"):
            error = status_data.get("error", "Unknown error")
            raise Exception(f"Video generation {status}: {error}")
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Video generation timed out after {timeout}s (request: {request_id})")


def download_video(video_url, save_path):
    """Download a video from fal.ai CDN to local path."""
    response = requests.get(video_url, stream=True, timeout=120)
    response.raise_for_status()
    
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return str(path)


def generate_scene_video(
    prompt,
    start_image_path,
    end_image_path=None,
    duration=5,
    generate_audio=True,
    save_path=None,
    progress_callback=None,
    timeout=600,
):
    """
    Full pipeline: upload images → submit → poll → download.
    
    Args:
        prompt: Video prompt (Kling 3 style)
        start_image_path: Path to start frame
        end_image_path: Optional path to end frame
        duration: Duration in seconds (3-15)
        generate_audio: Whether to generate audio
        save_path: Where to save the resulting video
        progress_callback: Optional callback(message, type)
        timeout: Max wait time in seconds
        
    Returns:
        dict with 'video_url', 'local_path', 'file_size', 'request_id'
    """
    if progress_callback:
        progress_callback("📤 Uploading images to fal.ai...", "info")
    
    # Submit
    submission = submit_video_generation(
        prompt=prompt,
        start_image_path=start_image_path,
        end_image_path=end_image_path,
        duration=duration,
        generate_audio=generate_audio,
    )
    
    request_id = submission["request_id"]
    status_url = submission.get("status_url")
    response_url = submission.get("response_url")
    if progress_callback:
        progress_callback(f"✅ Submitted (ID: {request_id[:16]}...). Waiting for completion...", "info")
    
    # Poll
    result = wait_for_completion(
        request_id,
        status_url=status_url,
        response_url=response_url,
        timeout=timeout,
        progress_callback=progress_callback,
    )
    
    video_data = result.get("video", {})
    video_url = video_data.get("url")
    
    if not video_url:
        raise Exception(f"No video URL in result: {result}")
    
    if progress_callback:
        size_mb = video_data.get("file_size", 0) / (1024 * 1024)
        progress_callback(f"🎬 Video ready ({size_mb:.1f} MB). Downloading...", "info")
    
    # Download
    local_path = None
    if save_path:
        local_path = download_video(video_url, save_path)
        if progress_callback:
            progress_callback(f"💾 Saved to {Path(save_path).name}", "success")
    
    return {
        "video_url": video_url,
        "local_path": local_path,
        "file_size": video_data.get("file_size", 0),
        "request_id": request_id,
    }
