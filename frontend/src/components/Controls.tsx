import { useState, useEffect } from "react";
import type { Preferences } from "../types";
import { saveSettings } from "../storage";

interface Props {
  onGenerate: (
    distanceM: number,
    mode: "walk" | "cycle" | "drive",
    preferences: Preferences
  ) => void;
  loading: boolean;
  initialDistance: number;
  initialMode: "walk" | "cycle" | "drive";
  initialPreferences: Preferences;
}

function Slider({
  label,
  value,
  onChange,
  leftLabel,
  rightLabel,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  leftLabel: string;
  rightLabel: string;
}) {
  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-slate-600 mb-1">
        {label}
      </label>
      <input
        type="range"
        min={0}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
      />
      <div className="flex justify-between text-[10px] text-slate-400">
        <span>{leftLabel}</span>
        <span>{rightLabel}</span>
      </div>
    </div>
  );
}

export default function Controls({
  onGenerate,
  loading,
  initialDistance,
  initialMode,
  initialPreferences,
}: Props) {
  const [distanceKm, setDistanceKm] = useState(initialDistance);
  const [mode, setMode] = useState<"walk" | "cycle" | "drive">(initialMode);
  const [preferences, setPreferences] = useState<Preferences>(initialPreferences);

  // Persist settings on change
  useEffect(() => {
    saveSettings({ distanceKm, mode, preferences });
  }, [distanceKm, mode, preferences]);

  const updatePref = (key: keyof Preferences, val: number) => {
    setPreferences((p) => ({ ...p, [key]: val }));
  };

  return (
    <div className="p-4">
      <p className="text-xs text-slate-500 mb-4">
        Click the map to set your start location, then configure and generate.
      </p>

      {/* Distance */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Distance: {distanceKm} km
        </label>
        <input
          type="range"
          min={1}
          max={50}
          step={0.5}
          value={distanceKm}
          onChange={(e) => setDistanceKm(Number(e.target.value))}
          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
        <div className="flex justify-between text-[10px] text-slate-400">
          <span>1 km</span>
          <span>50 km</span>
        </div>
      </div>

      {/* Mode */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Mode
        </label>
        <div className="flex gap-1">
          {(["walk", "cycle", "drive"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 px-3 py-1.5 text-sm rounded ${
                mode === m
                  ? "bg-blue-500 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {m === "walk" ? "Walk" : m === "cycle" ? "Cycle" : "Drive"}
            </button>
          ))}
        </div>
      </div>

      {/* Preferences */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-slate-700 mb-2">
          Preferences
        </h3>
        <Slider
          label="Terrain"
          value={preferences.hilly}
          onChange={(v) => updatePref("hilly", v)}
          leftLabel="Flat"
          rightLabel="Hilly"
        />
        <Slider
          label="Surface"
          value={preferences.offroad}
          onChange={(v) => updatePref("offroad", v)}
          leftLabel="Paved roads"
          rightLabel="Trails / offroad"
        />
        <Slider
          label="Route overlap"
          value={preferences.repetition}
          onChange={(v) => updatePref("repetition", v)}
          leftLabel="No repeats"
          rightLabel="Don't care"
        />
        <Slider
          label="Green space"
          value={preferences.green}
          onChange={(v) => updatePref("green", v)}
          leftLabel="Don't care"
          rightLabel="Maximize"
        />
      </div>

      {/* Generate button */}
      <button
        onClick={() => onGenerate(distanceKm * 1000, mode, preferences)}
        disabled={loading}
        className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-slate-300 text-white font-medium py-2 px-4 rounded transition"
      >
        {loading ? "Generating..." : "Generate Routes"}
      </button>
    </div>
  );
}
