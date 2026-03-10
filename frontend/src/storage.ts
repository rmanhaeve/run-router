import type { Preferences } from "./types";

const STORAGE_KEY = "circular-route-gen";

interface StoredSettings {
  startLocation: [number, number] | null;
  distanceKm: number;
  mode: "walk" | "cycle" | "drive";
  preferences: Preferences;
  mapView: { lat: number; lng: number; zoom: number } | null;
}

const DEFAULTS: StoredSettings = {
  startLocation: null,
  distanceKm: 5,
  mode: "walk",
  preferences: { hilly: 50, offroad: 50, repetition: 10, green: 50 },
  mapView: null,
};

export function loadSettings(): StoredSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    return { ...DEFAULTS, ...JSON.parse(raw) };
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
