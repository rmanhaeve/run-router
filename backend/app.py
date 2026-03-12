"""FastAPI backend for circular route generator.

Route generation algorithms by R. Lewis and P. Corcoran, Cardiff University.

Original publication:
  Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length
  Round Trips in Real-World Street Networks". Springer Nature Computer Science,
  vol. 5, 868. https://link.springer.com/article/10.1007/s42979-024-03223-3
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from models import GenerateRequest
from engine.valhalla_client import ValhallaClient
from engine.generator import generate_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Circular Route Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALHALLA_URL = os.environ.get("VALHALLA_URL", "http://localhost:8002")


@app.get("/api/health")
async def health():
    return {"status": "ok", "valhalla_url": VALHALLA_URL}


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    client = ValhallaClient(VALHALLA_URL)
    try:
        result = await generate_routes(
            source=req.start,
            target_distance=req.distance_m,
            mode=req.mode,
            preferences=req.preferences.model_dump(),
            valhalla_client=client,
            algorithm=req.algorithm,
            iterations=req.iterations,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Route generation failed")
        raise HTTPException(500, f"Route generation failed: {e}")


@app.post("/api/generate-stream")
async def generate_stream(req: GenerateRequest):
    """SSE endpoint for route generation with progress updates."""

    async def event_stream():
        progress_queue = asyncio.Queue()

        async def on_progress(step, pct):
            await progress_queue.put({"type": "progress", "step": step, "pct": pct})

        async def run_generation():
            client = ValhallaClient(VALHALLA_URL)
            try:
                result = await generate_routes(
                    source=req.start,
                    target_distance=req.distance_m,
                    mode=req.mode,
                    preferences=req.preferences.model_dump(),
                    valhalla_client=client,
                    algorithm=req.algorithm,
                    iterations=req.iterations,
                    on_progress=on_progress,
                )
                await progress_queue.put({"type": "result", "data": result})
            except Exception as e:
                await progress_queue.put({"type": "error", "message": str(e)})

        task = asyncio.create_task(run_generation())

        while True:
            msg = await progress_queue.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["type"] in ("result", "error"):
                break

        await task

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/export-gpx")
async def export_gpx(req: dict):
    """Convert route coordinates to GPX format."""
    coords = req.get("coordinates", [])
    name = req.get("name", "Circular Route")

    gpx = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="CircularRouteGenerator"
  xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>{name}</name>
    <trkseg>
"""
    for pt in coords:
        gpx += f'      <trkpt lat="{pt[1]}" lon="{pt[0]}"></trkpt>\n'
    gpx += """    </trkseg>
  </trk>
</gpx>"""

    return StreamingResponse(
        iter([gpx]),
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f'attachment; filename="{name}.gpx"'},
    )


# Serve frontend static files (when built into /app/static by the Dockerfile)
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback — serve index.html for any non-API, non-asset path."""
        file = STATIC_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
