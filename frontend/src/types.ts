export interface Preferences {
  hilly: number;
  offroad: number;
  repetition: number;
  crossings: number;
  tradeoff: number; // 0=distance accuracy only, 100=route quality only
}

export interface RouteMetrics {
  length: number;
  climb: number;
  climb_per_km: number;
  overlap_pct: number;
  offroad_pct: number;
  paved_pct: number;
}

export interface ElevationPoint {
  distance: number;
  elevation: number;
}

export interface SurfaceSegment {
  start: number;
  end: number;
  type: "paved" | "unpaved" | "unknown";
}

export interface Route {
  id: number;
  coordinates: [number, number][];
  metrics: RouteMetrics;
  score: number;
  costs: [number, number];
  elevation_profile: ElevationPoint[];
  surface_profile: SurfaceSegment[];
}

export interface GenerateResult {
  routes: Route[];
  isochrone: [number, number][];
  source: [number, number];
  target_distance: number;
  mode: string;
}

export interface GenerateRequest {
  start: [number, number];
  distance_m: number;
  mode: "walk" | "cycle";
  preferences: Preferences;
  algorithm: number;
  iterations: number;
}
