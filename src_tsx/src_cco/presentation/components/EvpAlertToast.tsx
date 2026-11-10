// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React, { useState } from 'react';
import { EmergencyVehicle } from '../../domain/models/EmergencyVehicle';
import fletPalette from '../styles/flet_color_palette.json';
import { Siren, ArrowRight, ChevronUp, ChevronDown } from 'lucide-react';

import { triggerHaptic } from '../utils/haptics';

interface EvpAlertToastProps {
  alerts: EmergencyVehicle[];
}

export const EvpAlertToast: React.FC<EvpAlertToastProps> = ({ alerts }) => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth < 768;
    }
    return false;
  });

  if (alerts.length === 0) return null;

  const preemptingAlerts = alerts.filter(
    (a) => Boolean(a.isEvpTriggered) || a.state === 'PREEMPTING' || Boolean(a.targetIntersection)
  );
  const transitAlerts = alerts.filter(
    (a) => !Boolean(a.isEvpTriggered) && a.state !== 'PREEMPTING' && !a.targetIntersection
  );

  // Collapsed mode: Displays only a compact pill for 100% unobstructed map view
  if (isCollapsed) {
    return (
      <div className="absolute top-2 sm:top-4 right-2 sm:right-4 z-30 pointer-events-auto">
        <button
          onClick={() => {
            triggerHaptic(15);
            setIsCollapsed(false);
          }}
          className="flex items-center gap-1.5 sm:gap-2 bg-[#263238]/95 hover:bg-[#37474F]/95 border border-rose-500/80 text-rose-300 px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-full shadow-xl backdrop-blur-md transition-all cursor-pointer text-xs font-semibold select-none"
          title="Clique para expandir alertas de emergência"
        >
          <Siren className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
          <span className="text-[11px] sm:text-xs">
            {preemptingAlerts.length > 0 && `${preemptingAlerts.length} Preempção`}
            {preemptingAlerts.length > 0 && transitAlerts.length > 0 && ' • '}
            {transitAlerts.length > 0 && `${transitAlerts.length} Em Trânsito`}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-0.5 sm:ml-1" />
        </button>
      </div>
    );
  }

  // Expanded mode: Responsive positioning without horizontal overflow
  return (
    <div className="absolute top-2 sm:top-4 right-2 sm:right-4 left-2 sm:left-auto z-30 flex flex-col gap-1.5 sm:gap-2 max-w-none sm:max-w-sm w-auto sm:w-full pointer-events-auto select-none transition-all">
      {/* Top control bar with collapse button */}
      <div className="flex items-center justify-between px-2 sm:px-2.5 py-1 bg-[#263238]/95 backdrop-blur-md rounded-lg border border-[#37474F] text-xs shadow-md">
        <div className="flex items-center gap-1.5 sm:gap-2 text-rose-400 font-bold tracking-wide text-[11px] sm:text-xs">
          <Siren className="w-3.5 h-3.5 animate-pulse shrink-0" />
          <span className="truncate">
            {preemptingAlerts.length > 0 && `${preemptingAlerts.length} ${preemptingAlerts.length === 1 ? 'Preempção' : 'Preempções'}`}
            {preemptingAlerts.length > 0 && transitAlerts.length > 0 && ' • '}
            {transitAlerts.length > 0 && `${transitAlerts.length} Trânsito`}
          </span>
        </div>
        <button
          onClick={() => {
            triggerHaptic(15);
            setIsCollapsed(true);
          }}
          className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-[#37474F] text-slate-300 hover:text-white text-[10px] sm:text-[11px] transition-colors cursor-pointer shrink-0"
          title="Minimizar alertas"
        >
          <span>Recolher</span>
          <ChevronUp className="w-3 h-3" />
        </button>
      </div>

      {alerts.slice(0, 3).map((vehicle) => {
        const corpUpper = String(vehicle.corporation || '').toUpperCase();
        const isSamu = corpUpper.includes('SAMU');
        const isBombeiro = corpUpper.includes('BOMB');

        let corpColor = fletPalette.evp.policia.alert;
        if (isSamu) {
          corpColor = fletPalette.evp.samu.alert;
        } else if (isBombeiro) {
          corpColor = fletPalette.evp.bombeiros.alert;
        }

        const isPreempting = Boolean(vehicle.isEvpTriggered) || vehicle.state === 'PREEMPTING' || Boolean(vehicle.targetIntersection);

        return (
          <div
            key={vehicle.vehicleId}
            style={{ borderColor: corpColor }}
            className="bg-[#263238]/95 border rounded-lg px-2.5 sm:px-3.5 py-2 sm:py-2.5 shadow-xl backdrop-blur-md flex items-center justify-between gap-2 text-slate-100"
          >
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <div
                style={{ borderColor: `${corpColor}55`, backgroundColor: `${corpColor}1A` }}
                className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center border shrink-0"
              >
                <Siren className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-pulse" style={{ color: corpColor }} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-bold text-xs tracking-wide truncate max-w-[100px] sm:max-w-none" style={{ color: corpColor }}>
                    {vehicle.corporation}
                  </span>
                  <span className="text-[10px] sm:text-[11px] px-1.5 py-0.2 rounded bg-[#37474F] text-slate-200 font-mono font-semibold shrink-0">
                    {vehicle.vehicleId}
                  </span>
                </div>
                <p className="text-[10px] sm:text-[11px] text-slate-300 mt-0.5 truncate">
                  Velocidade: <span className="font-mono font-semibold text-slate-100">{Math.round(vehicle.speedKmh)} km/h</span>
                  {vehicle.distanceToIntersectionMeters != null && (
                    <> • <span className="font-mono">{Math.round(vehicle.distanceToIntersectionMeters)}m</span></>
                  )}
                </p>
              </div>
            </div>

            {isPreempting ? (
              <div className="flex items-center gap-1 bg-cyan-950/80 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded border border-cyan-500/50 shrink-0">
                <span className="text-[8px] sm:text-[9px] text-cyan-300 font-bold uppercase hidden xs:inline">Preempção:</span>
                <span className="text-[10px] sm:text-xs font-mono font-bold text-cyan-200 truncate max-w-[70px] sm:max-w-[120px]">
                  {vehicle.targetIntersection || 'Ativa'}
                </span>
                <ArrowRight className="w-3 h-3 text-cyan-400 shrink-0" />
              </div>
            ) : (
              <div className="flex items-center gap-1 bg-amber-950/70 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded border border-amber-500/40 shrink-0">
                <span className="text-[9px] sm:text-[10px] text-amber-300 font-semibold whitespace-nowrap">Sirene</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
