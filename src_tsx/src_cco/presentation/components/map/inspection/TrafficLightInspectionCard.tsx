// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { RenderedTrafficLight } from '../../../hooks/useCcoMapLayers';
import { Radio } from 'lucide-react';

interface TrafficLightInspectionCardProps {
  trafficLight: RenderedTrafficLight;
}

export const TrafficLightInspectionHeader: React.FC<TrafficLightInspectionCardProps> = ({ trafficLight }) => (
  <>
    <span className="text-sm sm:text-base font-bold tracking-wide text-emerald-400 flex items-center gap-1.5">
      <Radio className="w-4 h-4 text-emerald-400" /> {trafficLight.id}
    </span>
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#37474F] dark:bg-slate-800 text-slate-200 font-mono font-semibold">
      Fase {trafficLight.phase}
    </span>
  </>
);

export const TrafficLightInspectionBody: React.FC<TrafficLightInspectionCardProps> = ({ trafficLight }) => (
  <>
    <div className="flex items-center justify-between">
      <span className="text-slate-400">Estado Operacional:</span>
      <span
        className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
          trafficLight.displayState === 'GREEN'
            ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/60'
            : trafficLight.displayState.includes('YELLOW')
            ? 'bg-amber-950 text-amber-300 border border-amber-500/60'
            : 'bg-rose-950 text-rose-300 border border-rose-500/60'
        }`}
      >
        {trafficLight.displayState}
      </span>
    </div>

    <div className="flex items-center justify-between">
      <span className="text-slate-400">Fase do Ciclo:</span>
      <span className="font-mono font-bold text-slate-100">
        Fase {trafficLight.phase} (Adaptativo CARINA)
      </span>
    </div>

    <div className="flex items-center justify-between">
      <span className="text-slate-400">Coordenadas SVG:</span>
      <span className="font-mono text-slate-300 text-[11px]">
        ({Math.round(trafficLight.cx)}, {Math.round(trafficLight.cy)})
      </span>
    </div>

    <div className="pt-2 border-t border-[#37474F] dark:border-slate-800">
      <div className="flex items-center gap-1.5 text-[11px] text-emerald-400">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span>Supervisionado por Fenix Watchdog</span>
      </div>
    </div>
  </>
);
