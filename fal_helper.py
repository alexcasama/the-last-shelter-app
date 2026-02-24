"""
The Last Shelter — fal.ai Helper
Upload images to fal storage and manage Kling 3 video generation API calls.
"""
import os
import json
import time
import base64
import httpx
import fal_client
from pathlib import Path


def get_fal_key():
    """Get FAL_KEY from environment."""
    key = os.environ.get("FAL_KEY", "")
    if not key:
        raise ValueError("FAL_KEY not set in environment. Add it to your .env file.")
    return key


def upload_image_to_fal(image_path):
    """
    Upload a local image to fal.ai storage for use in API calls.
    
    Args:
        image_path: Path to local image file
        
    Returns:
        URL of the uploaded image on fal storage
    """
    image_path = str(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    url = fal_client.upload_file(image_path)
    return url


def generate_video_kling_o3(
    start_image_url,
    prompt,
    end_image_url=None,
    elements=None,
    duration="10",
    generate_audio=True,
    aspect_ratio="16:9",
    use_pro=False,
):
    """
    Generate a video using Kling 3 Pro image-to-video or reference-to-video.
    
    Uses reference-to-video when elements are provided (character consistency),
    falls back to image-to-video when no elements are needed.
    
    Args:
        start_image_url: URL of the starting frame image (Frame A)
        prompt: Kling 3 cinematic prompt (motion + camera + audio)
        end_image_url: Optional URL of the ending frame image (Frame B)
        elements: Optional list of character elements for consistency
                  [{"frontal_image_url": "...", "reference_image_urls": ["..."]}]
        duration: Clip duration "3" to "15" seconds
        generate_audio: Whether to generate ambient audio
        aspect_ratio: "16:9", "9:16", or "1:1"
        use_pro: Use Pro tier (better quality, higher cost)
        
    Returns:
        Dict with video URL and metadata
    """
    tier = "pro" if use_pro else "standard"
    
    # Choose endpoint based on whether we have character elements
    if elements:
        endpoint = f"fal-ai/kling-video/o3/{tier}/reference-to-video"
        arguments = {
            "prompt": prompt,
            "start_image_url": start_image_url,
            "elements": elements,
            "duration": str(duration),
            "generate_audio": generate_audio,
            "aspect_ratio": aspect_ratio,
        }
        if end_image_url:
            arguments["end_image_url"] = end_image_url
    else:
        endpoint = f"fal-ai/kling-video/o3/{tier}/image-to-video"
        arguments = {
            "image_url": start_image_url,
            "prompt": prompt,
            "duration": str(duration),
            "generate_audio": generate_audio,
        }
        if end_image_url:
            arguments["end_image_url"] = end_image_url
    
    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"[Kling 3 Pro] {log['message']}")
    
    result = fal_client.subscribe(
        endpoint,
        arguments=arguments,
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    
    return {
        "video_url": result["video"]["url"],
        "file_size": result["video"].get("file_size", 0),
        "file_name": result["video"].get("file_name", "output.mp4"),
        "endpoint": endpoint,
        "duration": duration,
    }


def generate_video_kling_v3_pro(
    prompt,
    start_image_url=None,
    end_image_url=None,
    elements=None,
    voice_ids=None,
    duration="10",
    generate_audio=True,
    aspect_ratio="16:9",
    negative_prompt="blur, distort, and low quality",
    cfg_scale=0.5,
):
    """
    Generate a video using Kling V3 Pro image-to-video.
    
    Best for presenter clips with lip sync (voice_ids) and 
    high-quality cinematic generation.
    
    Args:
        prompt: Kling 3 prompt with dialogue format for lip sync
        start_image_url: Optional starting frame image URL
        end_image_url: Optional ending frame image URL
        elements: Optional character elements for consistency
        voice_ids: Optional list of voice IDs for lip sync
        duration: Clip duration "3" to "15"
        generate_audio: Must be True for lip sync
        aspect_ratio: "16:9", "9:16", or "1:1"
        negative_prompt: Things to avoid
        cfg_scale: 0-1, adherence to prompt
        
    Returns:
        Dict with video URL and metadata
    """
    endpoint = "fal-ai/kling-video/v3/pro/image-to-video"
    
    arguments = {
        "prompt": prompt,
        "duration": str(duration),
        "generate_audio": generate_audio,
        "aspect_ratio": aspect_ratio,
        "negative_prompt": negative_prompt,
        "cfg_scale": cfg_scale,
    }
    
    if start_image_url:
        arguments["start_image_url"] = start_image_url
    if end_image_url:
        arguments["end_image_url"] = end_image_url
    if elements:
        arguments["elements"] = elements
    if voice_ids:
        arguments["voice_ids"] = voice_ids
    
    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"[Kling V3 Pro] {log['message']}")
    
    result = fal_client.subscribe(
        endpoint,
        arguments=arguments,
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    
    return {
        "video_url": result["video"]["url"],
        "file_size": result["video"].get("file_size", 0),
        "file_name": result["video"].get("file_name", "output.mp4"),
        "endpoint": endpoint,
        "duration": duration,
    }


def create_voice(voice_audio_url):
    """
    Create a reusable voice ID from an audio/video sample.
    
    Args:
        voice_audio_url: URL to audio (.mp3/.wav) or video (.mp4/.mov), 5-30 seconds
        
    Returns:
        Voice ID string (reusable across all generations)
    """
    result = fal_client.subscribe(
        "fal-ai/kling-video/create-voice",
        arguments={"voice_url": voice_audio_url},
    )
    return result["voice_id"]


def download_video(video_url, output_path):
    """
    Download a generated video from fal storage to local file.
    
    Args:
        video_url: URL of the video on fal storage
        output_path: Local path to save the video
        
    Returns:
        Path to saved video file
    """
    output_path = str(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with httpx.Client(timeout=120) as client:
        response = client.get(video_url)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
    
    return output_path
