import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Route } from "../types";

// Fix Leaflet default marker icon
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const ROUTE_COLORS = [
  "#3b82f6", // blue
  "#ef4444", // red
  "#22c55e", // green
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#f97316", // orange
];

interface Props {
  routes: Route[];
  selectedRoute: Route | null;
  isochrone: [number, number][] | null;
  startLocation: [number, number] | null;
  initialMapView: { lat: number; lng: number; zoom: number } | null;
  onMapClick: (lon: number, lat: number) => void;
  onMapMoved: (lat: number, lng: number, zoom: number) => void;
  hoveredPointIndex?: number | null;
}

export default function RouteMap({
  routes,
  selectedRoute,
  isochrone,
  startLocation,
  initialMapView,
  onMapClick,
  onMapMoved,
  hoveredPointIndex,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layersRef = useRef<{
    marker: L.Marker | null;
    isochrone: L.Polygon | null;
    routes: L.Polyline[];
    hoverMarker: L.CircleMarker | null;
  }>({ marker: null, isochrone: null, routes: [], hoverMarker: null });

  // Initialize map — restore saved view or use default
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const center: [number, number] = initialMapView
      ? [initialMapView.lat, initialMapView.lng]
      : [51.48, -3.72];
    const zoom = initialMapView?.zoom ?? 13;
    const map = L.map(containerRef.current).setView(center, zoom);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    map.on("click", (e: L.LeafletMouseEvent) => {
      onMapClick(e.latlng.lng, e.latlng.lat);
    });

    // Persist view on move/zoom
    map.on("moveend", () => {
      const c = map.getCenter();
      onMapMoved(c.lat, c.lng, map.getZoom());
    });

    // Fly to user location when geolocation succeeds
    map.on("locationfound", (e: L.LocationEvent) => {
      map.flyTo(e.latlng, 14);
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update click handler ref
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.off("click");
    mapRef.current.on("click", (e: L.LeafletMouseEvent) => {
      onMapClick(e.latlng.lng, e.latlng.lat);
    });
  }, [onMapClick]);

  // Start marker
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (layersRef.current.marker) {
      layersRef.current.marker.remove();
      layersRef.current.marker = null;
    }
    if (startLocation) {
      const marker = L.marker([startLocation[1], startLocation[0]])
        .addTo(map)
        .bindPopup("Start Location");
      layersRef.current.marker = marker;
      map.setView([startLocation[1], startLocation[0]], map.getZoom());
    }
  }, [startLocation]);

  // Isochrone
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (layersRef.current.isochrone) {
      layersRef.current.isochrone.remove();
      layersRef.current.isochrone = null;
    }
    if (isochrone) {
      const latlngs = isochrone.map(
        ([lon, lat]) => [lat, lon] as [number, number]
      );
      const poly = L.polygon(latlngs, {
        color: "#94a3b8",
        fillColor: "#94a3b8",
        fillOpacity: 0.15,
        weight: 1,
      }).addTo(map);
      layersRef.current.isochrone = poly;
    }
  }, [isochrone]);

  // Routes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old
    for (const line of layersRef.current.routes) {
      line.remove();
    }
    layersRef.current.routes = [];

    if (routes.length === 0) return;

    const bounds = L.latLngBounds([]);

    for (const route of routes) {
      const isSelected = selectedRoute?.id === route.id;
      const latlngs = route.coordinates.map(
        ([lon, lat]) => [lat, lon] as [number, number]
      );
      const color = ROUTE_COLORS[route.id % ROUTE_COLORS.length];
      const line = L.polyline(latlngs, {
        color,
        weight: isSelected ? 5 : 2,
        opacity: isSelected ? 1 : 0.4,
      }).addTo(map);
      line.bindPopup(
        `<b>Route ${route.id + 1}</b><br>` +
          `${(route.metrics.length / 1000).toFixed(1)} km | ` +
          `${route.metrics.climb}m climb | ` +
          `Score: ${route.score}`
      );
      layersRef.current.routes.push(line);
      for (const ll of latlngs) bounds.extend(ll);
    }

    map.fitBounds(bounds, { padding: [30, 30] });
  }, [routes, selectedRoute]);

  // Elevation profile hover marker
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (layersRef.current.hoverMarker) {
      layersRef.current.hoverMarker.remove();
      layersRef.current.hoverMarker = null;
    }

    if (hoveredPointIndex == null || !selectedRoute) return;

    const coord = selectedRoute.coordinates[hoveredPointIndex];
    if (!coord) return;

    const [lon, lat] = coord;
    layersRef.current.hoverMarker = L.circleMarker([lat, lon], {
      radius: 7,
      color: "#fff",
      weight: 2,
      fillColor: ROUTE_COLORS[selectedRoute.id % ROUTE_COLORS.length],
      fillOpacity: 1,
      interactive: false,
    }).addTo(map);
  }, [hoveredPointIndex, selectedRoute]);

  const handleLocate = () => {
    mapRef.current?.locate({ setView: false, maxZoom: 14 });
  };

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      <button
        onClick={handleLocate}
        title="Zoom to my location"
        className="absolute top-3 right-3 z-[1000] bg-white border-2 border-slate-300 rounded-md w-8 h-8 flex items-center justify-center shadow hover:bg-slate-50 cursor-pointer text-base leading-none"
      >
        &#8982;
      </button>
    </div>
  );
}
