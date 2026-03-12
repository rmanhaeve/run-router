import { useState, useEffect } from "react";
import type { Preferences } from "../types";
import { saveSettings } from "../storage";

interface Props {
  onGenerate: (
    distanceM: number,
    mode: "walk" | "cycle",
    preferences: Preferences
  ) => void;
  loading: boolean;
  initialDistance: number;
  initialMode: "walk" | "cycle";
  initialPreferences: Preferences;
}

/** Three-way toggle for symmetric preferences (e.g. flat vs hilly) */
function PreferenceToggle({
  label,
  value,
  onChange,
  leftLabel,
  centerLabel,
  rightLabel,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  leftLabel: string;
  centerLabel: string;
  rightLabel: string;
}) {
  const options = [
    { val: 0, text: leftLabel },
    { val: 50, text: centerLabel },
    { val: 100, text: rightLabel },
  ];
  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-slate-600 mb-1">
        {label}
      </label>
      <div className="flex gap-1">
        {options.map((opt) => (
          <button
            key={opt.val}
            onClick={() => onChange(opt.val)}
            className={`flex-1 px-2 py-1 text-xs rounded transition ${
              value === opt.val
                ? "bg-blue-500 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {opt.text}
          </button>
        ))}
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
  const [mode, setMode] = useState<"walk" | "cycle">(initialMode);
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
          {(["walk", "cycle"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 px-3 py-1.5 text-sm rounded ${
                mode === m
                  ? "bg-blue-500 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {m === "walk" ? "Walk" : "Cycle"}
            </button>
          ))}
        </div>
      </div>

      {/* Preferences */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-slate-700 mb-2">
          Preferences
        </h3>
        <PreferenceToggle
          label="Terrain"
          value={preferences.hilly}
          onChange={(v) => updatePref("hilly", v)}
          leftLabel="Flat"
          centerLabel="No preference"
          rightLabel="Hilly"
        />
        <PreferenceToggle
          label="Surface"
          value={preferences.offroad}
          onChange={(v) => updatePref("offroad", v)}
          leftLabel="Paved"
          centerLabel="No preference"
          rightLabel="Trails"
        />
        <PreferenceToggle
          label="Route overlap"
          value={preferences.repetition}
          onChange={(v) => updatePref("repetition", v)}
          leftLabel="No repeats"
          centerLabel="Some OK"
          rightLabel="Don't care"
        />
        <PreferenceToggle
          label="Green space"
          value={preferences.green}
          onChange={(v) => updatePref("green", v)}
          leftLabel="Don't care"
          centerLabel="Some green"
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
