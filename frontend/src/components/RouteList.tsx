import type { Route } from "../types";
import { exportGpx } from "../api";

const COLORS = [
  "#3b82f6",
  "#ef4444",
  "#22c55e",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#f97316",
];

interface Props {
  routes: Route[];
  selectedId: number | null;
  targetDistance: number;
  onSelect: (route: Route) => void;
}

export default function RouteList({
  routes,
  selectedId,
  targetDistance,
  onSelect,
}: Props) {
  return (
    <div className="border-t border-slate-200">
      <h3 className="text-sm font-medium text-slate-700 px-4 pt-3 pb-1">
        {routes.length} route{routes.length !== 1 ? "s" : ""} found
      </h3>
      <div className="divide-y divide-slate-100">
        {routes.map((route) => {
          const isSelected = route.id === selectedId;
          const color = COLORS[route.id % COLORS.length];
          const lengthKm = (route.metrics.length / 1000).toFixed(1);
          const errorPct = Math.abs(
            ((route.metrics.length - targetDistance) / targetDistance) * 100
          ).toFixed(0);

          return (
            <div
              key={route.id}
              onClick={() => onSelect(route)}
              className={`px-4 py-2 cursor-pointer hover:bg-slate-50 transition ${
                isSelected ? "bg-blue-50 border-l-4 border-blue-500" : ""
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="text-sm font-medium">
                  Route {route.id + 1}
                </span>
                <span className="text-xs text-slate-400 ml-auto">
                  Score: {route.score}
                </span>
              </div>
              <div className="text-xs text-slate-500 ml-5 grid grid-cols-2 gap-x-4 gap-y-0.5">
                <span>
                  {lengthKm} km ({errorPct}% off)
                </span>
                <span>{route.metrics.climb}m climb</span>
                <span>{route.metrics.offroad_pct}% offroad</span>
                <span>{route.metrics.overlap_pct}% overlap</span>
              </div>
              {isSelected && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    exportGpx(
                      route.coordinates,
                      `route-${route.id + 1}`
                    );
                  }}
                  className="mt-1 ml-5 text-xs text-blue-500 hover:underline"
                >
                  Export GPX
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
