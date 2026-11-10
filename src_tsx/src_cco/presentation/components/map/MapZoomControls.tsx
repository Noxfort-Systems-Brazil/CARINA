// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

import { triggerHaptic } from '../../utils/haptics';

interface MapZoomControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}

export const MapZoomControls: React.FC<MapZoomControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onReset,
}) => {
  return (
    <div className="absolute bottom-3 right-2 sm:bottom-4 sm:right-4 z-10 flex items-center gap-1 sm:gap-1.5 bg-[#263238]/90 backdrop-blur-md border border-[#37474F] rounded-lg p-1 text-slate-200 shadow-xl pointer-events-auto select-none">
      <button
        onClick={() => {
          triggerHaptic(15);
          onZoomIn();
        }}
        className="p-1.5 sm:p-1.5 hover:bg-[#37474F] rounded text-slate-300 hover:text-white transition-colors cursor-pointer"
        title="Aproximar (+)"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
      <button
        onClick={() => {
          triggerHaptic(15);
          onZoomOut();
        }}
        className="p-1.5 sm:p-1.5 hover:bg-[#37474F] rounded text-slate-300 hover:text-white transition-colors cursor-pointer"
        title="Afastar (-)"
      >
        <ZoomOut className="w-4 h-4" />
      </button>
      <div className="h-4 w-px bg-[#455A64]" />
      <button
        onClick={() => {
          triggerHaptic(20);
          onReset();
        }}
        className="p-1.5 hover:bg-[#37474F] rounded text-slate-300 hover:text-white transition-colors flex items-center gap-1 text-[10px] sm:text-[11px] font-mono px-1.5 sm:px-2 cursor-pointer"
        title="Recentralizar Vista (0)"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span>Reset</span>
      </button>
    </div>
  );
};
