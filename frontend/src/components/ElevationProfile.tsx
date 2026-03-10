import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { Route } from "../types";

interface Props {
  route: Route;
}

export default function ElevationProfile({ route }: Props) {
  const data = route.elevation_profile.map((pt) => ({
    distance: Math.round(pt.distance),
    elevation: pt.elevation,
  }));

  // Build surface color segments for reference bar
  const surfaceData = route.surface_profile;

  return (
    <div className="h-full flex flex-col p-2">
      <div className="flex items-center gap-4 text-xs text-slate-500 mb-1 px-2">
        <span className="font-medium text-slate-700">
          Route {route.id + 1} Elevation
        </span>
        <span>{route.metrics.climb}m total climb</span>
        <span>{route.metrics.climb_per_km} m/km</span>
        <div className="ml-auto flex gap-3">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-gray-400" />
            paved
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            unpaved
          </span>
        </div>
      </div>

      {/* Surface bar */}
      <div className="h-2 flex rounded overflow-hidden mx-2 mb-1">
        {surfaceData.map((seg, i) => {
          const totalDist =
            route.elevation_profile[route.elevation_profile.length - 1]
              ?.distance || 1;
          const widthPct = ((seg.end - seg.start) / totalDist) * 100;
          const color =
            seg.type === "paved"
              ? "#9ca3af"
              : seg.type === "unpaved"
              ? "#22c55e"
              : "#fbbf24";
          return (
            <div
              key={i}
              style={{ width: `${widthPct}%`, backgroundColor: color }}
            />
          );
        })}
      </div>

      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <XAxis
              dataKey="distance"
              tickFormatter={(v) => `${(v / 1000).toFixed(1)}km`}
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10 }}
              domain={["dataMin - 10", "dataMax + 10"]}
              tickFormatter={(v) => `${v}m`}
              width={45}
            />
            <Tooltip
              formatter={(val: number) => [`${val}m`, "Elevation"]}
              labelFormatter={(v) => `${(Number(v) / 1000).toFixed(2)} km`}
            />
            <Area
              type="monotone"
              dataKey="elevation"
              stroke="#3b82f6"
              fill="#93c5fd"
              fillOpacity={0.4}
              strokeWidth={1.5}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
