// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React from 'react';
import { EmergencyVehicle } from '../../../../domain/models/EmergencyVehicle';
import { Navigation, Gauge, Shield, Siren } from 'lucide-react';

interface VehicleInspectionCardProps {
  vehicle: EmergencyVehicle;
}

export const VehicleInspectionHeader: React.FC<VehicleInspectionCardProps> = ({ vehicle }) => (
  <>
    <span className="text-sm sm:text-base font-bold tracking-wide text-cyan-300">
      🚨 {vehicle.vehicleId}
    </span>
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#37474F] dark:bg-slate-800 text-slate-200 font-mono font-semibold uppercase">
      {vehicle.corporation}
    </span>
  </>
);

export const VehicleInspectionBody: React.FC<VehicleInspectionCardProps> = ({ vehicle }) => (
  <>
    <div className="flex items-center justify-between">
      <span className="text-slate-400 flex items-center gap-1.5">
        <Gauge className="w-3.5 h-3.5 text-cyan-400" /> Velocidade:
      </span>
      <span className="font-mono font-bold text-slate-100">
        {Math.round(vehicle.speedKmh)} km/h
      </span>
    </div>

    <div className="flex items-center justify-between">
      <span className="text-slate-400 flex items-center gap-1.5">
        <Navigation className="w-3.5 h-3.5 text-cyan-400" /> Proa / Direção:
      </span>
      <span className="font-mono font-bold text-slate-100">
        {Math.round(vehicle.headingDeg || 0)}°
      </span>
    </div>

    <div className="flex items-center justify-between">
      <span className="text-slate-400 flex items-center gap-1.5">
        <Siren className="w-3.5 h-3.5 text-rose-400" /> Modo Sirene:
      </span>
      <span
        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
          vehicle.sirenActive
            ? 'bg-rose-950 text-rose-300 border border-rose-500/50'
            : 'bg-[#37474F] dark:bg-slate-800 text-slate-300'
        }`}
      >
        {vehicle.sirenActive ? 'SIRENE ATIVA' : 'PATRULHA'}
      </span>
    </div>

    <div className="flex items-center justify-between">
      <span className="text-slate-400 flex items-center gap-1.5">
        <Shield className="w-3.5 h-3.5 text-emerald-400" /> Preempção Semafórica:
      </span>
      <span
        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
          vehicle.isEvpTriggered || vehicle.state === 'PREEMPTING'
            ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/50'
            : 'bg-[#37474F] dark:bg-slate-800 text-slate-300'
        }`}
      >
        {vehicle.isEvpTriggered || vehicle.state === 'PREEMPTING'
          ? 'CORREDOR VERDE'
          : 'INATIVA'}
      </span>
    </div>

    {vehicle.targetIntersection && (
      <div className="pt-2 border-t border-[#37474F] dark:border-slate-800 flex items-center justify-between">
        <span className="text-slate-400 text-[11px]">Cruzamento Alvo:</span>
        <span className="font-mono font-bold text-cyan-300 text-xs">
          {vehicle.targetIntersection}
        </span>
      </div>
    )}
  </>
);
