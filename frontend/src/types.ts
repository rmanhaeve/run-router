export interface Preferences {
  hilly: number;
  offroad: number;
  repetition: number;
  green: number;
}

export interface RouteMetrics {
  length: number;
  climb: number;
  climb_per_km: number;
  overlap_pct: number;
  offroad_pct: number;
  paved_pct: number;
  avg_green: number;
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
  mode: "walk" | "cycle" | "drive";
  preferences: Preferences;
  algorithm: number;
  iterations: number;
}
