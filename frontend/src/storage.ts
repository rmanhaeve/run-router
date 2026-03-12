import type { Preferences } from "./types";

const STORAGE_KEY = "circular-route-gen";

interface StoredSettings {
  startLocation: [number, number] | null;
  distanceKm: number;
  mode: "walk" | "cycle";
  preferences: Preferences;
  mapView: { lat: number; lng: number; zoom: number } | null;
}

const DEFAULTS: StoredSettings = {
  startLocation: null,
  distanceKm: 5,
  mode: "walk",
  preferences: { hilly: 50, offroad: 50, repetition: 0, crossings: 0, tradeoff: 50 },
  mapView: null,
};

export function loadSettings(): StoredSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    const parsed = { ...DEFAULTS, ...JSON.parse(raw) };
    // Migrate: if stored mode was "drive", reset to "walk"
    if (parsed.mode === "drive") parsed.mode = "walk";
    // Migrate: add tradeoff if missing from stored preferences
    if (parsed.preferences.tradeoff === undefined) parsed.preferences.tradeoff = 50;
    // Migrate: replace green with crossings
    if ((parsed.preferences as any).green !== undefined) delete (parsed.preferences as any).green;
    if (parsed.preferences.crossings === undefined) parsed.preferences.crossings = 0;
    return parsed;
  } catch {
    return DEFAULTS;
  }
}

export function saveSettings(partial: Partial<StoredSettings>) {
  try {
    const current = loadSettings();
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...current, ...partial }));
  } catch {
    // localStorage unavailable
  }
}
