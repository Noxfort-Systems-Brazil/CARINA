// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Siren, Radio, MapPin, Activity } from 'lucide-react';
import { EmergencyVehicle } from '../../../domain/models/EmergencyVehicle';
import { RenderedTrafficLight, RenderedIntersection } from '../../hooks/useCcoMapLayers';
import { RenderedStreet } from '../../../domain/services/StreetTopologyGrouperService';
import { triggerHaptic } from '../../utils/haptics';

export interface SearchTarget {
  type: 'vehicle' | 'trafficLight' | 'intersection' | 'street';
  id: string;
  title: string;
  subtitle: string;
  x: number;
  y: number;
  payload: any;
}

interface QuickSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  vehicles: EmergencyVehicle[];
  trafficLights: RenderedTrafficLight[];
  intersections: RenderedIntersection[];
  streets: RenderedStreet[];
  onSelectTarget: (target: SearchTarget) => void;
}

export const QuickSearchModal: React.FC<QuickSearchModalProps> = ({
  isOpen,
  onClose,
  vehicles,
  trafficLights,
  intersections,
  streets,
  onSelectTarget,
}) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const normalizedQuery = query.trim().toLowerCase();

  const results: SearchTarget[] = [];

  // Filter vehicles
  for (const v of vehicles) {
    if (
      !normalizedQuery ||
      v.vehicleId.toLowerCase().includes(normalizedQuery) ||
      v.corporation.toLowerCase().includes(normalizedQuery)
    ) {
      results.push({
        type: 'vehicle',
        id: v.vehicleId,
        title: `${v.corporation}: ${v.vehicleId}`,
        subtitle: `${Math.round(v.speedKmh)} km/h • ${v.sirenActive ? '🚨 Sirene Ativa' : 'Patrulha'}`,
        x: v.x,
        y: v.y,
        payload: v,
      });
    }
  }

  // Filter traffic lights
  for (const tl of trafficLights) {
    if (
      !normalizedQuery ||
      tl.id.toLowerCase().includes(normalizedQuery) ||
      `semáforo ${tl.id}`.toLowerCase().includes(normalizedQuery)
    ) {
      results.push({
        type: 'trafficLight',
        id: tl.id,
        title: `Semáforo ${tl.id}`,
        subtitle: `Fase ${tl.phase} • Estado: ${tl.displayState}`,
        x: tl.cx,
        y: tl.cy,
        payload: tl,
      });
    }
  }

  // Filter intersections
  for (const n of intersections.slice(0, 15)) {
    if (
      !normalizedQuery ||
      n.id.toLowerCase().includes(normalizedQuery) ||
      `cruzamento ${n.id}`.toLowerCase().includes(normalizedQuery)
    ) {
      results.push({
        type: 'intersection',
        id: n.id,
        title: `Cruzamento ${n.id}`,
        subtitle: `Nó viário de convergência`,
        x: n.cx,
        y: n.cy,
        payload: n,
      });
    }
  }

  // Filter streets
  for (const s of streets.slice(0, 20)) {
    if (s.name && (!normalizedQuery || s.name.toLowerCase().includes(normalizedQuery))) {
      results.push({
        type: 'street',
        id: s.id,
        title: s.name,
        subtitle: `Congestionamento: ${Math.round(s.congestion)}%`,
        x: 0,
        y: 0,
        payload: s,
      });
    }
  }

  const handleSelect = (target: SearchTarget) => {
    triggerHaptic(20);
    onSelectTarget(target);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-start justify-center pt-14 sm:pt-20 px-3 select-none"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-[#263238] dark:bg-slate-900 border border-[#37474F] dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[75vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-2.5 px-3.5 py-3 border-b border-[#37474F] dark:border-slate-800">
          <Search className="w-4 h-4 text-cyan-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar viatura, semáforo, rua..."
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-400 outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 hover:bg-[#37474F] dark:hover:bg-slate-800 rounded text-slate-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onClose}
            className="text-xs px-2 py-1 rounded bg-[#37474F] dark:bg-slate-800 text-slate-300 hover:text-white font-mono"
          >
            Esc
          </button>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {results.length === 0 ? (
            <div className="p-6 text-center text-slate-400 text-xs">
              Nenhum elemento encontrado para "{query}".
            </div>
          ) : (
            results.slice(0, 30).map((item) => (
              <div
                key={`${item.type}-${item.id}`}
                onClick={() => handleSelect(item)}
                className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[#37474F]/80 dark:hover:bg-slate-800/80 cursor-pointer transition-colors"
              >
                <div className="w-7 h-7 rounded-lg bg-black/30 flex items-center justify-center shrink-0">
                  {item.type === 'vehicle' && <Siren className="w-3.5 h-3.5 text-rose-400" />}
                  {item.type === 'trafficLight' && <Radio className="w-3.5 h-3.5 text-emerald-400" />}
                  {item.type === 'intersection' && <MapPin className="w-3.5 h-3.5 text-cyan-400" />}
                  {item.type === 'street' && <Activity className="w-3.5 h-3.5 text-amber-400" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-bold text-slate-100 truncate">{item.title}</div>
                  <div className="text-[10px] text-slate-400 truncate">{item.subtitle}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
