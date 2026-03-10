# Circular Route Generator

A web-based tool for generating circular (round-trip) routes of a target distance from a chosen start location. Configure preferences for terrain, surface type, route overlap, and green space, then pick from multiple scored suggestions.

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
- Walking, cycling, or driving modes
- Preference sliders: flat/hilly, paved/offroad, overlap tolerance, green space
- Multiple route suggestions ranked by preference score (Pareto front)
- Elevation profile with surface type overlay
- GPX export

## Data sources

All routing data comes from [OpenRouteService](https://openrouteservice.org/) (built on [OpenStreetMap](https://www.openstreetmap.org/)):

| Data | Source |
|------|--------|
| Road network & routing | ORS Directions API |
| Reachable area | ORS Isochrone API |
| Elevation | ORS (SRTM) |
| Surface type | ORS `extra_info=surface` (OSM tags) |
| Green space | ORS `extra_info=green` (OSM land use) |

## Setup

### Docker (recommended)

```bash
ORS_API_KEY="your-key-here" docker compose up --build
```

Open http://localhost:8000.

### Prerequisites (local dev)

- Python 3.10+, [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- An OpenRouteService API key (free at https://openrouteservice.org/dev/#/signup)

### Backend

```bash
cd backend
uv venv
uv pip install -r requirements.txt
export ORS_API_KEY="your-key-here"
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
  app.py              FastAPI server
  models.py           Request/response models
  engine/
    generator.py      Route generation orchestrator
    ors_client.py     Async OpenRouteService API client
    graph.py          Smooth graph construction & Pareto optimization
    scoring.py        Multi-preference route scoring
    polygons.py       Ellipse/polygon geometry
    distance.py       Haversine distance utilities

frontend/
  src/
    App.tsx           Main app layout
    api.ts            Backend API client (SSE streaming)
    components/
      Map.tsx         Leaflet map with route display
      Controls.tsx    Distance, mode & preference controls
      RouteList.tsx   Scored route list with GPX export
      ElevationProfile.tsx  Elevation chart (Recharts)
```
