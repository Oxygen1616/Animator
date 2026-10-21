"""Builds the FastAPI app: Web Studio UI, REST API for agents, and Supabase routes if configured."""
from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .routers import generate, health, videos, agent
from .settings import get_settings


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Animator · Whiteboard Video Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0f172a;
      --card: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --accent: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      border-bottom: 1px solid var(--border);
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(15, 23, 42, 0.8);
      backdrop-filter: blur(8px);
    }
    .logo-container { display: flex; align-items: center; gap: 0.75rem; }
    .logo { width: 32px; height: 32px; border-radius: 8px; }
    h1 { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.025em; }
    .badge {
      font-size: 0.75rem;
      background: rgba(59, 130, 246, 0.2);
      color: #60a5fa;
      padding: 0.2rem 0.5rem;
      border-radius: 9999px;
      font-weight: 600;
      border: 1px solid rgba(59, 130, 246, 0.4);
    }
    main {
      flex: 1;
      max-width: 1000px;
      margin: 2rem auto;
      width: 100%;
      padding: 0 1.5rem;
      display: grid;
      grid-template-columns: 1fr;
      gap: 2rem;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
    }
    h2 { font-size: 1.1rem; margin-bottom: 1rem; color: #f1f5f9; display: flex; align-items: center; gap: 0.5rem; }
    label { display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 0.5rem; color: var(--muted); }
    textarea, select, input {
      width: 100%;
      padding: 0.75rem 1rem;
      background: #0b1120;
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text);
      font-family: inherit;
      font-size: 0.95rem;
      margin-bottom: 1.25rem;
    }
    textarea:focus, select:focus, input:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 1px var(--primary);
    }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }
    @media (max-width: 768px) {
      .grid-3 { grid-template-columns: 1fr; }
    }
    button {
      background: var(--primary);
      color: white;
      border: none;
      border-radius: 8px;
      padding: 0.75rem 1.5rem;
      font-weight: 600;
      cursor: pointer;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      font-size: 1rem;
      transition: background 0.15s;
    }
    button:hover { background: var(--primary-hover); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    pre {
      background: #0b1120;
      padding: 1rem;
      border-radius: 8px;
      overflow-x: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      color: #38bdf8;
      border: 1px solid var(--border);
    }
    .status-box {
      margin-top: 1rem;
      padding: 1rem;
      border-radius: 8px;
      background: #0b1120;
      border: 1px solid var(--border);
      display: none;
    }
    video { width: 100%; border-radius: 8px; margin-top: 1rem; background: #000; }
    .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
    .tab { background: none; border: none; color: var(--muted); padding: 0.5rem 1rem; cursor: pointer; width: auto; font-size: 0.9rem; }
    .tab.active { color: var(--primary); font-weight: 600; border-bottom: 2px solid var(--primary); border-radius: 0; }
  </style>
</head>
<body>
  <header>
    <div class="logo-container">
      <svg class="logo" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#222B38"/><path d="M7 21c3-7 6-11 8-11s1 8 3 8 3-5 7-9" fill="none" stroke="#5B8CFF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <h1>Animator</h1>
      <span class="badge">umbrelOS Agent Ready</span>
    </div>
    <div>
      <a href="/api/docs" target="_blank" style="color: #60a5fa; text-decoration: none; font-size: 0.875rem; font-weight: 500;">Interactive API Docs ↗</a>
    </div>
  </header>

  <main>
    <div class="card">
      <div class="tabs">
        <button type="button" class="tab active" onclick="switchTab('studio')">Studio Generator</button>
        <button type="button" class="tab" onclick="switchTab('agent')">Agent API & Integration Docs</button>
      </div>

      <div id="tab-studio">
        <form id="gen-form" onsubmit="handleGenerate(event)">
          <label for="prompt">Topic or Explanation Prompt</label>
          <textarea id="prompt" rows="3" placeholder="e.g. How wings create lift when a plane flies..." required></textarea>

          <div class="grid-3">
            <div>
              <label for="scenes">Target Scenes</label>
              <select id="scenes">
                <option value="" selected>Auto (Ideal 3–5 scenes)</option>
                <option value="1">1 Scene (Quick tip)</option>
                <option value="2">2 Scenes</option>
                <option value="3">3 Scenes</option>
                <option value="4">4 Scenes</option>
                <option value="5">5 Scenes</option>
                <option value="6">6 Scenes</option>
                <option value="7">7 Scenes</option>
                <option value="8">8 Scenes (Comprehensive)</option>
              </select>
            </div>
            <div>
              <label for="voice">Narration Voice</label>
              <select id="voice">
                <option value="Kore" selected>Kore (Natural Female)</option>
                <option value="Puck">Puck (Energetic Male)</option>
                <option value="Fenrir">Fenrir (Deep Male)</option>
                <option value="Aoede">Aoede (Warm Female)</option>
                <option value="Zephyr">Zephyr (Smooth Male)</option>
                <option value="Leda">Leda (Calm Female)</option>
                <option value="Charon">Charon (Authoritative Male)</option>
                <option value="Orus">Orus (Direct Male)</option>
              </select>
            </div>
            <div>
              <label for="quality">Render Quality</label>
              <select id="quality">
                <option value="low">Low (Fast 20fps)</option>
                <option value="medium" selected>Medium (Standard 24fps)</option>
                <option value="high">High (HQ 24fps 3Mbps)</option>
              </select>
            </div>
          </div>

          <label for="gemini_key">Google Gemini API Key (optional if set in Umbrel env)</label>
          <input type="password" id="gemini_key" placeholder="AIzaSy...">

          <button type="submit" id="btn-submit">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            Generate Whiteboard Video
          </button>
        </form>

        <div id="status-box" class="status-box">
          <p id="status-text" style="font-weight: 500;"></p>
          <div id="video-container"></div>
        </div>
      </div>

      <div id="tab-agent" style="display: none;">
        <h2>🤖 Calling Animator from Umbrel AI Agents</h2>
        <p style="color: var(--muted); margin-bottom: 1rem; font-size: 0.9rem;">
          Any agent running on umbrelOS (Hermes Agent, OpenClaw, Agent Zero, or external scripts) can trigger whiteboard generation via the local REST API.
        </p>

        <label>Endpoint</label>
        <pre>POST http://umbrel.local:8002/api/generate
Internal (Docker network): http://oxygen-animator_server_1:8000/api/generate</pre>
        <br>

        <label>cURL Example</label>
        <pre>curl -X POST http://umbrel.local:8002/api/generate \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "How photosynthesis works",
    "scenes": 4,
    "voice": "Kore",
    "quality": "medium"
  }'</pre>
        <br>

        <label>Agent Python Skill / Code Snippet</label>
        <pre>import requests, time

# 1. Submit animation task
res = requests.post("http://umbrel.local:8002/api/generate", json={
    "prompt": "How photosynthesis works",
    "scenes": 4,
    "voice": "Kore"
}).json()
job_id = res["job_id"]

# 2. Poll until finished
while True:
    status = requests.get(f"http://umbrel.local:8002/api/status/{job_id}").json()
    if status["status"] == "ready":
        print(f"Video ready: http://umbrel.local:8002{status['video_url']}")
        break
    elif status["status"] == "failed":
        print("Generation failed:", status.get("detail"))
        break
    time.sleep(3)</pre>
      </div>
    </div>
  </main>

  <script>
    function switchTab(name) {
      document.getElementById('tab-studio').style.display = name === 'studio' ? 'block' : 'none';
      document.getElementById('tab-agent').style.display = name === 'agent' ? 'block' : 'none';
      document.querySelectorAll('.tab').forEach((t, i) => {
        t.classList.toggle('active', (name === 'studio' && i === 0) || (name === 'agent' && i === 1));
      });
    }

    async function handleGenerate(e) {
      e.preventDefault();
      const prompt = document.getElementById('prompt').value;
      const scenesVal = document.getElementById('scenes').value;
      const scenes = scenesVal ? parseInt(scenesVal, 10) : null;
      const voice = document.getElementById('voice').value;
      const quality = document.getElementById('quality').value;
      const key = document.getElementById('gemini_key').value;
      const btn = document.getElementById('btn-submit');
      const box = document.getElementById('status-box');
      const text = document.getElementById('status-text');
      const vc = document.getElementById('video-container');

      btn.disabled = true;
      box.style.display = 'block';
      text.innerText = 'Submitting job to Animator pipeline...';
      vc.innerHTML = '';

      try {
        const payload = { prompt, voice, quality };
        if (scenes) payload.scenes = scenes;
        if (key) payload.gemini_api_key = key;

        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to start generation');

        text.innerText = 'Rendering scenes (writing script, drawing icons, generating speech)...';
        pollJob(data.job_id);
      } catch (err) {
        text.innerText = 'Error: ' + err.message;
        btn.disabled = false;
      }
    }

    async function pollJob(jobId) {
      const text = document.getElementById('status-text');
      const btn = document.getElementById('btn-submit');
      const vc = document.getElementById('video-container');

      const interval = setInterval(async () => {
        try {
          const res = await fetch(`/api/status/${jobId}`);
          const data = await res.json();
          if (data.status === 'ready') {
            clearInterval(interval);
            text.innerText = 'Render complete!';
            btn.disabled = false;
            vc.innerHTML = `<video controls autoplay src="${data.video_url}"></video><div style="margin-top: 0.5rem;"><a href="${data.video_url}" download style="color: #60a5fa; text-decoration: none; font-weight: 600;">Download MP4 ⬇</a></div>`;
          } else if (data.status === 'failed') {
            clearInterval(interval);
            text.innerText = 'Render failed: ' + (data.detail || 'Unknown error');
            btn.disabled = false;
          }
        } catch (e) {
          clearInterval(interval);
          text.innerText = 'Status check failed: ' + e.message;
          btn.disabled = false;
        }
      }, 3000);
    }
  </script>
</body>
</html>
"""


def create_app() -> FastAPI:
    app = FastAPI(
        title="Animator API",
        description="Type an idea, get a narrated hand-drawn whiteboard explainer video. Accessible to web browsers and AI agents.",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Agent router mounted under /api and /api/v1
    app.include_router(agent.router, prefix="/api")
    app.include_router(agent.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api")
    app.include_router(health.router, prefix="/api/v1")

    # If Supabase is configured, also mount the SaaS routers
    if settings.supabase_url and settings.supabase_secret_key:
        app.include_router(generate.router, prefix="/api")
        app.include_router(videos.router, prefix="/api")

    @app.get("/", response_class=HTMLResponse)
    async def index_page():
        return HTMLResponse(INDEX_HTML)

    return app
