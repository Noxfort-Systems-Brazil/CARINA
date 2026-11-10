// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React, { useState } from 'react';
import { Compass, ChevronDown } from 'lucide-react';
import fletPalette from '../../styles/flet_color_palette.json';

import { triggerHaptic } from '../../utils/haptics';

export const MapLegend: React.FC = () => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth < 768;
    }
    return false;
  });

  if (isCollapsed) {
    return (
      <div className="absolute bottom-3 left-2 sm:bottom-4 sm:left-4 z-10 pointer-events-auto select-none">
        <button
          onClick={() => {
            triggerHaptic(15);
            setIsCollapsed(false);
          }}
          className="flex items-center gap-1.5 bg-[#263238]/95 hover:bg-[#37474F]/95 border border-[#37474F] rounded-lg px-2.5 py-1.5 text-xs text-slate-200 shadow-xl backdrop-blur-md transition-all cursor-pointer"
          title="Exibir Legenda Operacional"
        >
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-medium text-slate-200">Legenda</span>
        </button>
      </div>
    );
  }

  return (
    <div className="absolute bottom-3 left-2 sm:bottom-4 sm:left-4 z-10 bg-[#263238]/90 backdrop-blur-md border border-[#37474F] rounded-lg px-2.5 sm:px-3.5 py-2 sm:py-2.5 text-xs text-slate-200 shadow-xl pointer-events-auto select-none max-w-[calc(100vw-6rem)] sm:max-w-none">
      <div className="flex items-center justify-between gap-2 mb-1.5 font-semibold text-[10px] sm:text-[11px] text-slate-300 uppercase tracking-wider">
        <div className="flex items-center gap-1.5">
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          <span>Legenda Operacional</span>
        </div>
        <button
          onClick={() => {
            triggerHaptic(15);
            setIsCollapsed(true);
          }}
          className="p-0.5 rounded hover:bg-[#37474F] text-slate-400 hover:text-white transition-colors cursor-pointer"
          title="Minimizar legenda"
        >
          <ChevronDown className="w-3 h-3" />
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2 sm:gap-4">
        {/* Heatmap Bar */}
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] sm:text-[10px] text-slate-400">Heatmap:</span>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" style={{ backgroundColor: fletPalette.heatmap.freeFlow }} title="Fluxo Livre (0-25%)" />
            <span className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" style={{ backgroundColor: fletPalette.heatmap.moderate }} title="Moderado (25-50%)" />
            <span className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" style={{ backgroundColor: fletPalette.heatmap.retention }} title="Retenção (50-75%)" />
            <span className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" style={{ backgroundColor: fletPalette.heatmap.intense }} title="Intenso (75-90%)" />
            <span className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full" style={{ backgroundColor: fletPalette.heatmap.congested }} title="Congestionado (90-100%)" />
          </div>
        </div>
        <div className="hidden sm:block h-3.5 w-px bg-slate-700" />
        {/* Semáforos */}
        <div className="flex items-center gap-1">
          <span className="text-[9px] sm:text-[10px] text-slate-400">Semáforos:</span>
          <span className="w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full" style={{ backgroundColor: fletPalette.trafficLights.green }} />
          <span className="w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full" style={{ backgroundColor: fletPalette.trafficLights.yellow }} />
          <span className="w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full" style={{ backgroundColor: fletPalette.trafficLights.red }} />
        </div>
        <div className="hidden sm:block h-3.5 w-px bg-[#455A64]" />
        {/* Viaturas EVP */}
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="text-[9px] sm:text-[10px] text-slate-300">EVP:</span>
          <div className="flex items-center gap-1" title="SAMU (Triângulo)">
            <svg width="9" height="9" viewBox="-6 -6 12 12" className="inline-block">
              <polygon points="0,-5 5,5 -5,5" fill={fletPalette.evp.samu.alert} stroke="#FFFFFF" strokeWidth="0.8" />
            </svg>
            <span className="text-[9px] sm:text-[10px] text-slate-200">SAMU</span>
          </div>
          <div className="flex items-center gap-1" title="Bombeiros (Quadrado)">
            <span className="inline-block w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-xs border border-white/60" style={{ backgroundColor: fletPalette.evp.bombeiros.base }} />
            <span className="text-[9px] sm:text-[10px] text-slate-200">Bombeiros</span>
          </div>
          <div className="flex items-center gap-1" title="Polícia (Círculo)">
            <span className="inline-block w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full border border-white/60" style={{ backgroundColor: fletPalette.evp.policia.alert }} />
            <span className="text-[9px] sm:text-[10px] text-slate-200">Polícia</span>
          </div>
        </div>
      </div>
    </div>
  );
};
