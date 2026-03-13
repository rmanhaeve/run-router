# Circular Route Generator

A web-based tool for generating circular (round-trip) routes of a target distance from a chosen start location. Configure preferences for terrain, surface type, route overlap, and road crossings, then pick from multiple scored suggestions.

## Based on

The route generation engine is based on the algorithms described in:

> Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length Round Trips in Real-World Street Networks". *Springer Nature Computer Science*, vol. 5, 868.
> https://link.springer.com/article/10.1007/s42979-024-03223-3

Original implementation by:
- **R. Lewis**, School of Mathematics, Cardiff University, Wales — [www.rhydlewis.eu](http://www.rhydlewis.eu), LewisR9@cardiff.ac.uk
- **P. Corcoran**, School of Computer Science and Informatics, Cardiff University, Wales — corcoranp@cardiff.ac.uk

Original source code: https://zenodo.org/doi/10.5281/zenodo.8154412

### Copyright notice (original code)

Redistribution and use of this source code, with or without modification, are permitted provided that a citation is made to the publication given above. Neither the name of the University nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission. This software is provided by the contributors "as is" and any express or implied warranties, including, but not limited to, the implied warranties of merchantability and fitness for a particular purpose are disclaimed. In no event shall the contributors be liable for any direct, indirect, incidental, special, exemplary, or consequential damages (including, but not limited to, procurement of substitute goods or services; loss of use, data, or profits; or business interruption) however caused and on any theory of liability, whether in contract, strict liability, or tort (including negligence or otherwise) arising in any way out of the use of this software, even if advised of the possibility of such damage. This software is supplied without any support services.

## Features

- Click-to-set start location on an interactive map
- Target distance from 1 to 50 km
- Walking and cycling modes
- Preference controls: flat/hilly terrain, paved/offroad surface, overlap tolerance, road crossing avoidance
- Multiple route suggestions ranked by preference score (Pareto front)
- Elevation profile with surface type overlay
- GPX export

## Data sources

All routing data comes from a self-hosted [Valhalla](https://github.com/valhalla/valhalla) instance (built on [OpenStreetMap](https://www.openstreetmap.org/)):

| Data | Source |
|------|--------|
| Road network & routing | Valhalla `/route` API |
| Reachable area | Valhalla `/isochrone` API |
| Elevation | Valhalla `/height` API (SRTM) |
| Surface type | Valhalla maneuver `unpaved` attribute |

## Setup

### Prerequisites

You need a running Valhalla instance loaded with an OSM extract for your area. The easiest way:

```bash
docker run -p 8002:8002 \
  -v $PWD/valhalla_tiles:/custom_files \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest
```

See [gis-ops/docker-valhalla](https://github.com/gis-ops/docker-valhalla) for instructions on loading an OSM extract.

### Docker (recommended)

```bash
VALHALLA_URL="http://your-valhalla-host:8002" docker compose up --build
```

Open http://localhost:8000.

### Prerequisites (local dev)

- Python 3.10+, [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- A running Valhalla instance (default: `http://localhost:8002`)

### Backend

```bash
cd backend
uv venv
uv pip install -r requirements.txt
export VALHALLA_URL="http://localhost:8002"
.venv/bin/uvicorn app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (Vite dev server proxies `/api` to the backend).

## Project structure

```
backend/
  app.py                FastAPI server
  models.py             Request/response models
  engine/
    generator.py        Route generation orchestrator
    valhalla_client.py  Async Valhalla API client
    graph.py            Smooth graph construction & Pareto optimization
    scoring.py          Multi-preference route scoring
    local_search.py     Multi-objective local search
    polygons.py         Ellipse/polygon geometry
    distance.py         Haversine distance utilities

frontend/
  src/
    App.tsx             Main app layout
    api.ts              Backend API client (SSE streaming)
    components/
      Map.tsx           Leaflet map with route display
      Controls.tsx      Distance, mode & preference controls
      RouteList.tsx     Scored route list with GPX export
      ElevationProfile.tsx  Elevation chart (Recharts)
```
