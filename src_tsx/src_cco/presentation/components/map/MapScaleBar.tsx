// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';

interface MapScaleBarProps {
  zoom: number;
  scaleFactor?: number;
}

export const MapScaleBar: React.FC<MapScaleBarProps> = ({ zoom, scaleFactor = 1.0 }) => {
  // 1 unit in SUMO coordinates corresponds to 1 meter in real world
  const effectiveScale = Math.max(scaleFactor * zoom, 0.001);
  const targetPixels = 75; // Target visual bar width in pixels
  const rawMeters = targetPixels / effectiveScale;

  const candidateSteps = [10, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000];
  let chosenMeters = candidateSteps[0];
  let minDiff = Math.abs(rawMeters - chosenMeters);

  for (const step of candidateSteps) {
    const diff = Math.abs(rawMeters - step);
    if (diff < minDiff) {
      minDiff = diff;
      chosenMeters = step;
    }
  }

  const barWidthPx = Math.min(Math.max(chosenMeters * effectiveScale, 35), 140);
  const label = chosenMeters >= 1000 ? `${chosenMeters / 1000} km` : `${chosenMeters} m`;

  return (
    <div className="absolute bottom-3 left-24 sm:bottom-4 sm:left-32 z-10 select-none pointer-events-none flex flex-col items-center bg-white/80 dark:bg-slate-900/80 px-2 py-0.5 rounded backdrop-blur-xs border border-slate-300 dark:border-slate-700 shadow-xs">
      <span className="text-[9px] font-mono font-bold tracking-wider text-slate-700 dark:text-slate-300">
        {label}
      </span>
      <div
        style={{ width: `${barWidthPx}px` }}
        className="h-1 border-b-2 border-l-2 border-r-2 border-slate-800 dark:border-slate-200"
      />
    </div>
  );
};
