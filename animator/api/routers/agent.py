"""Direct agent router for local and networked AI agents (Hermes Agent, OpenClaw, Agent Zero, Claude, etc.)
Allows generating animated whiteboard videos from prompts or custom image sequences without external SaaS accounts.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Query
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from google import genai

from ...gemini.pipeline import StoryboardOptions, render_storyboard
from ...gemini.settings import (
    DEFAULT_TEXT_MODEL,
    DEFAULT_REGION_MODEL,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_TTS_MODEL,
    DEFAULT_VOICE,
)
from ...render import Scene, render_video
from ..settings import get_settings

router = APIRouter(tags=["agents"])

OUTPUT_DIR = Path(os.environ.get("ANIMATOR_OUTPUT_DIR", "/app/outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Track active and completed jobs in memory
JOBS: Dict[str, Dict[str, Any]] = {}

AVAILABLE_VOICES = ["Kore", "Puck", "Fenrir", "Aoede", "Charon", "Zephyr", "Leda", "Orus"]


class AgentGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Idea or script to turn into a narrated whiteboard animation (e.g. 'How photosynthesis works')")
    scenes: Optional[int] = Field(None, description="Exact number of scenes to generate (default: auto, 3-5)")
    voice: Optional[str] = Field("Kore", description="Gemini TTS voice name (default 'Kore')")
    quality: Optional[str] = Field("medium", description="Render quality: 'low' (20fps), 'medium' (24fps 1.5M), 'high' (24fps 3.0M)")
    gemini_api_key: Optional[str] = Field(None, description="Optional per-request Gemini API key. If omitted, uses GEMINI_API_KEY environment variable.")


class AgentJobResponse(BaseModel):
    job_id: str
    status: str
    prompt: str
    video_url: Optional[str] = None
    detail: Optional[str] = None


@router.get("/voices")
def list_voices():
    """List available TTS voice options for whiteboard narration."""
    return {"voices": AVAILABLE_VOICES, "default": "Kore"}


@router.post("/generate", response_model=AgentJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_video(
    request: AgentGenerateRequest,
    background_tasks: BackgroundTasks
) -> AgentJobResponse:
    """
    Trigger an AI whiteboard explainer video generation.
    Returns 202 Accepted with a job_id that agents can poll via /api/status/{job_id}.
    Once finished, the video is available at /api/videos/{job_id}.mp4.
    """
    settings = get_settings()
    api_key = request.gemini_api_key or settings.gemini_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Gemini API key. Pass 'gemini_api_key' in request JSON or set GEMINI_API_KEY environment variable."
        )

    job_id = f"anim_{uuid.uuid4().hex[:10]}"
    output_filename = f"{job_id}.mp4"
    output_path = OUTPUT_DIR / output_filename

    JOBS[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "prompt": request.prompt,
        "video_url": f"/api/videos/{output_filename}",
        "error": None
    }

    async def _run_pipeline():
        try:
            google_client = genai.Client(api_key=api_key)
            text_model = os.environ.get("GEMINI_MODEL") or DEFAULT_TEXT_MODEL
            region_model = os.environ.get("GEMINI_REGION_MODEL") or DEFAULT_REGION_MODEL
            image_model = os.environ.get("GEMINI_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL
            tts_model = os.environ.get("GEMINI_TTS_MODEL") or DEFAULT_TTS_MODEL

            options = StoryboardOptions(
                idea=request.prompt,
                output=output_path,
                quality=request.quality or "medium",
                text_model=text_model,
                region_model=region_model,
                image_model=image_model,
                tts_model=tts_model,
                voice=request.voice or DEFAULT_VOICE,
                num_scenes=request.scenes,
                save_assets=False,
            )
            with tempfile.TemporaryDirectory() as tmp_dir:
                await render_storyboard(google_client, options, Path(tmp_dir))
            JOBS[job_id]["status"] = "ready"
        except Exception as e:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)

    background_tasks.add_task(_run_pipeline)

    return AgentJobResponse(
        job_id=job_id,
        status="processing",
        prompt=request.prompt,
        video_url=f"/api/videos/{output_filename}",
        detail="Video generation queued. Poll /api/status/{job_id} until status is 'ready'."
    )


@router.get("/status/{job_id}", response_model=AgentJobResponse)
def get_job_status(job_id: str) -> AgentJobResponse:
    """Poll progress of a whiteboard animation job."""
    if job_id not in JOBS:
        output_filename = f"{job_id}.mp4"
        if (OUTPUT_DIR / output_filename).exists():
            return AgentJobResponse(
                job_id=job_id,
                status="ready",
                prompt="",
                video_url=f"/api/videos/{output_filename}"
            )
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = JOBS[job_id]
    return AgentJobResponse(
        job_id=job_id,
        status=job["status"],
        prompt=job["prompt"],
        video_url=job["video_url"] if job["status"] == "ready" else None,
        detail=job.get("error")
    )


@router.get("/videos/{filename}")
def download_video(filename: str):
    """Download or stream rendered MP4 video file."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(file_path, media_type="video/mp4", filename=filename)
