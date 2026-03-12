import { useState, useCallback, useEffect } from "react";
import type {
  GenerateResult,
  Route,
  Preferences,
  GenerateRequest,
} from "./types";
import { generateRoutes } from "./api";
import { loadSettings, saveSettings } from "./storage";
import RouteMap from "./components/Map";
import Controls from "./components/Controls";
import RouteList from "./components/RouteList";
import ElevationProfile from "./components/ElevationProfile";

const initial = loadSettings();

export default function App() {
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState("");
  const [progressPct, setProgressPct] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [hoveredElevIndex, setHoveredElevIndex] = useState<number | null>(null);

  const [startLocation, setStartLocation] = useState<[number, number] | null>(
    initial.startLocation
  );

  // Persist start location
  useEffect(() => {
    saveSettings({ startLocation });
  }, [startLocation]);

  const handleGenerate = useCallback(
    async (
      distanceM: number,
      mode: "walk" | "cycle",
      preferences: Preferences
    ) => {
      if (!startLocation) {
        setError("Click the map to set a start location first");
        return;
      }
      setLoading(true);
      setError(null);
      setResult(null);
      setSelectedRoute(null);
      setProgressStep("Starting...");
      setProgressPct(0);

      const req: GenerateRequest = {
        start: startLocation,
        distance_m: distanceM,
        mode,
        preferences,
        algorithm: 1,
        iterations: 2,
      };

      try {
        const res = await generateRoutes(req, (step, pct) => {
          setProgressStep(step);
          setProgressPct(pct);
        });
        setResult(res);
        if (res.routes.length > 0) {
          setSelectedRoute(res.routes[0]);
        }
      } catch (e: any) {
        setError(e.message || "Generation failed");
      } finally {
        setLoading(false);
      }
    },
    [startLocation]
  );

  const handleMapClick = useCallback(
    (lon: number, lat: number) => {
      if (!loading) {
        setStartLocation([lon, lat]);
      }
    },
    [loading]
  );

  const handleMapMoved = useCallback(
    (lat: number, lng: number, zoom: number) => {
      saveSettings({ mapView: { lat, lng, zoom } });
    },
    []
  );

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 text-white px-4 py-2 flex items-center gap-4 shrink-0">
        <h1 className="text-lg font-semibold">Circular Route Generator</h1>
        {startLocation && (
          <span className="text-sm text-slate-300">
            Start: {startLocation[1].toFixed(5)}, {startLocation[0].toFixed(5)}
          </span>
        )}
        {loading && (
          <div className="flex items-center gap-2 ml-auto">
            <div className="w-32 bg-slate-600 rounded-full h-2">
              <div
                className="bg-blue-400 h-2 rounded-full transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <span className="text-sm text-slate-300">{progressStep}</span>
          </div>
        )}
      </header>

      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 px-4 py-2 text-sm shrink-0">
          {error}
          <button
            className="ml-4 underline"
            onClick={() => setError(null)}
          >
            dismiss
          </button>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar: controls */}
        <div className="w-80 border-r border-slate-200 overflow-y-auto shrink-0 bg-white">
          <Controls
            onGenerate={handleGenerate}
            loading={loading}
            initialDistance={initial.distanceKm}
            initialMode={initial.mode}
            initialPreferences={initial.preferences}
          />

          {result && result.routes.length > 0 && (
            <RouteList
              routes={result.routes}
              selectedId={selectedRoute?.id ?? null}
              targetDistance={result.target_distance}
              onSelect={(r) => { setSelectedRoute(r); setHoveredElevIndex(null); }}
            />
          )}
        </div>

        {/* Map */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1">
            <RouteMap
              routes={result?.routes ?? []}
              selectedRoute={selectedRoute}
              isochrone={result?.isochrone ?? null}
              startLocation={startLocation}
              initialMapView={initial.mapView}
              onMapClick={handleMapClick}
              onMapMoved={handleMapMoved}
              hoveredPointIndex={hoveredElevIndex}
            />
          </div>

          {/* Elevation profile */}
          {selectedRoute && (
            <div className="h-48 border-t border-slate-200 bg-white shrink-0">
              <ElevationProfile route={selectedRoute} onHover={setHoveredElevIndex} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
